import hashlib,json,platform,subprocess,tempfile,time
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.baseline.service import baseline_service
from app.challenges.service import challenge_service
from app.confounders.service import confounder_service
from app.decision.service import decision_service
from app.measurement import measurement_attempt_service
from app.ml.config import FEATURE_REVISION,MODEL_DIR,MODEL_REVISION
from app.ml.runtime import MLRuntime,ml_runtime
from app.quality.models import MeasurementQualification
from app.runtime import RuntimePipelineStatus,runtime_service
from app.scenario import ScenarioType,scenario_provider
from app.simulation.bioimpedance.service import bioimpedance_service
from app.simulation.engine import simulation_engine
from app.simulation.sensors.models import SensorWindowRequest
from app.simulation.sensors.service import wearable_sensor_service
from app.temporal.service import temporal_service
from app.timeline.service import timeline_service
from app.verification.models import ReleaseStatus,VerificationCheck,VerificationReport,VerificationSection,VerificationStatus,overall_for


REVISION='aequor-release-verification-v1'
ROOT=Path(__file__).resolve().parents[3]
OUTPUT_DIR=ROOT/'verification'


class ReleaseVerificationService:
 def __init__(self):self._latest=None
 def _baseline(self):
  baseline_service.start()
  for index in range(28):
   attempt=measurement_attempt_service.attempt(SensorWindowRequest());baseline_service.capture(attempt.processed_features)
   if index<27:simulation_engine.step(6*3600 if index<24 else 12*3600)
  baseline_service.finalize();return baseline_service.snapshot()
 @staticmethod
 def _check(section,check_id,title,critical,ok,evidence,details='',warning=False,failure_reason=None):
  status=VerificationStatus.WARNING if warning else VerificationStatus.PASS if ok else VerificationStatus.FAIL
  section.append(VerificationCheck(check_id=check_id,title=title,category=check_id.split('.')[0],status=status,critical=critical,duration_ms=0,evidence=evidence,details=details or title,failure_reason=failure_reason if not ok else None))
 @staticmethod
 def _keys(value):
  if isinstance(value,dict):return set(value)|{k for child in value.values() for k in ReleaseVerificationService._keys(child)}
  if isinstance(value,list):return {k for child in value for k in ReleaseVerificationService._keys(child)}
  return set()
 def run(self,write_reports=True):
  from app.main import app
  started=datetime.now(timezone.utc);sections=[];summary={};client=TestClient(app)
  def section(identifier,title):
   value=VerificationSection(section_id=identifier,title=title,checks=[]);sections.append(value);return value.checks
  def check(s,i,t,c,ok,evidence,details='',warning=False,reason=None):self._check(s,i,t,c,ok,evidence,details,warning,reason)
  try:
   s=section('environment','Environment and model artifact')
   version=platform.python_version();supported=(3,11)<=tuple(map(int,version.split('.')[:2]));check(s,'environment.python','Supported Python runtime',True,supported,{'python':version})
   required=[ROOT/'frontend/package.json',ROOT/'frontend/package-lock.json',MODEL_DIR/f'{MODEL_REVISION}-int8.tflite',MODEL_DIR/f'{MODEL_REVISION}.metadata.json']
   for path in required:check(s,f'environment.file.{path.name}',f'Required file: {path.name}',True,path.exists(),{'path':str(path),'exists':path.exists()})
   artifact,metadata=required[2],required[3];digest=hashlib.sha256(artifact.read_bytes()).hexdigest() if artifact.exists() else None;meta=json.loads(metadata.read_text()) if metadata.exists() else {}
   check(s,'environment.model_hash','Model SHA-256 matches metadata',True,digest==meta.get('artifacts',{}).get('int8_sha256'),{'actual':digest,'expected':meta.get('artifacts',{}).get('int8_sha256')})
   status=ml_runtime.status();check(s,'environment.model_load','INT8 model loads',True,status['loaded'],status)
   if ml_runtime._interpreter:
    inp=ml_runtime._interpreter.get_input_details()[0];out=ml_runtime._interpreter.get_output_details()[0]
    check(s,'environment.tensor_shape','Model tensor shapes match 34-value adapter',True,int(inp['shape'][-1])==34 and int(out['shape'][-1])==34,{'input':inp['shape'].tolist(),'output':out['shape'].tolist()})
    check(s,'environment.quantization','INT8 quantization metadata exists',True,bool(inp['quantization'][0]) and bool(out['quantization'][0]),{'input_quantization':list(inp['quantization']),'output_quantization':list(out['quantization'])})
   else:check(s,'environment.tensor_shape','Model tensor shapes match',True,False,{});check(s,'environment.quantization','INT8 quantization metadata exists',True,False,{})

   s=section('services','Core service readiness');system=client.get('/api/v1/system/status').json()
   mapping={'digital_patient':'digital_patient_engine','bis_digital_twin':'bioimpedance_digital_twin','virtual_imu':'virtual_imu','virtual_temperature':'virtual_temperature','virtual_contact':'virtual_contact','quality':'quality_engine','signal_processing':'signal_processing','baseline':'baseline_engine','scenario':'scenario_engine','ml':'ml_engine','temporal':'temporal_engine','confounder':'confounder_engine','decision':'decision_engine'}
   for label,field in mapping.items():check(s,f'services.{label}',f'{label.replace("_"," ").title()} ready',True,system[field]=='READY',{'status':system[field]})
   check(s,'services.runtime','Integrated runtime ready',True,runtime_service.status()['ready'],runtime_service.status())

   s=section('reset','Deterministic reset');simulation_engine.reset();base=baseline_service.snapshot();scenario=scenario_provider.state();check(s,'reset.baseline','Baseline reset',True,base.state.value=='UNINITIALIZED',{'state':base.state.value});check(s,'reset.scenario','Scenario reset',True,scenario.scenario_type is ScenarioType.BASELINE_STABLE and not scenario.active,scenario.as_dict());check(s,'reset.temporal','Temporal history empty',True,len(temporal_service.history())==0,{'count':len(temporal_service.history())});check(s,'reset.decision','Decision history empty',True,len(decision_service.history())==0,{'count':len(decision_service.history())});check(s,'reset.runtime','Runtime history empty',True,len(runtime_service.history())==0,{'count':len(runtime_service.history())});check(s,'reset.indices','Acquisition indices reset',True,bioimpedance_service._sweep_index==0 and wearable_sensor_service._window_index==0,{'sweep_index':bioimpedance_service._sweep_index,'window_index':wearable_sensor_service._window_index})
   deterministic=[]
   for _ in range(2):simulation_engine.reset();cycle=runtime_service.measure(SensorWindowRequest());p=cycle.attempt.bis_sweep.left.points[0];deterministic.append((p.resistance_ohm,p.reactance_ohm,cycle.attempt.quality_assessment.overall_score))
   check(s,'reset.reproducible','Startup sequence reproduces deterministically',True,deterministic[0]==deterministic[1],{'runs':deterministic})

   s=section('baseline','Baseline calibration');simulation_engine.reset();base=self._baseline();check(s,'baseline.ready','Baseline reaches READY',True,base.state.value=='READY',base.model_dump(mode='json'));check(s,'baseline.count','Exactly 28 qualified observations enrolled',True,base.observation_count==28,{'count':base.observation_count});check(s,'baseline.span','Minimum simulated span satisfied',True,base.simulated_span_seconds>=base.minimum_simulated_span_seconds,{'actual':base.simulated_span_seconds,'minimum':base.minimum_simulated_span_seconds});check(s,'baseline.revisions','Feature and baseline revisions match',True,base.feature_revision==FEATURE_REVISION and base.baseline_revision=='baseline-v1',{'feature':base.feature_revision,'baseline':base.baseline_revision});check(s,'baseline.scenario','Calibration remained baseline-stable',True,scenario_provider.state().scenario_type is ScenarioType.BASELINE_STABLE and not scenario_provider.state().active,scenario_provider.state().as_dict())

   s=section('stable','Baseline-stable complete path');stable=[]
   for _ in range(3):stable.append(runtime_service.measure(SensorWindowRequest()))
   latest=stable[-1];a=latest.attempt
   for name,value in [('quality',a.quality_assessment.qualification is MeasurementQualification.QUALIFIED),('bis',a.bis_sweep is not None),('features',a.processed_features is not None),('baseline_comparison',a.baseline_comparison is not None),('tflite',a.ml_inference is not None),('temporal',a.temporal_assessment is not None),('confounder',a.confounder_assessment is not None),('decision',a.decision_snapshot is not None)]:check(s,f'stable.{name}',f'Stable path produces {name}',True,value,{'available':value})
   adis=[x.attempt.decision_snapshot.adi for x in stable];check(s,'stable.state','Stable cycles remain within personal baseline',True,all(x.current_surveillance_state=='WITHIN_PERSONAL_BASELINE' for x in stable),{'adi_range':[min(adis),max(adis)],'states':[x.current_surveillance_state for x in stable]})

   s=section('quality','Technical quality gating');quality_results={}
   for cid in ('active-motion','poor-contact','posture-transition'):
    result=challenge_service.run(cid);quality_results[cid]=result.model_dump(mode='json');check(s,f'quality.{cid}',f'{result.title} blocks rejected downstream data',True,result.status.value=='PASS',result.observed_evidence.model_dump(mode='json'))

   s=section('longitudinal','Longitudinal scenarios');left=challenge_service.run('arm-symmetry');arms=left.observed_evidence.observations
   check(s,'longitudinal.left','Slow LEFT direction and persistence',True,arms['left_run']['side']=='LEFT' and arms['left_run']['state']=='PERSISTENT_DEVIATION',arms['left_run']);check(s,'longitudinal.right','Slow RIGHT reverses direction',True,arms['right_run']['side']=='RIGHT' and arms['right_run']['state']=='PERSISTENT_DEVIATION',arms['right_run']);check(s,'longitudinal.symmetry','LEFT/RIGHT ADI within engineering tolerance',True,arms['adi_absolute_difference']<=arms['engineering_tolerance'],{'difference':arms['adi_absolute_difference'],'tolerance':arms['engineering_tolerance']})
   systemic=challenge_service.run('systemic-shift');check(s,'longitudinal.systemic','Systemic evidence rises and restrains unilateral escalation',True,systemic.status.value=='PASS',systemic.observed_evidence.observations)
   transient=challenge_service.run('transient-spike');check(s,'longitudinal.transient','One transient does not create persistent state',True,transient.status.value=='PASS',transient.observed_evidence.observations)
   recovery=challenge_service.run('scenario-reset');check(s,'longitudinal.reset','Scenario reset alone preserves decision',True,recovery.status.value=='PASS',recovery.observed_evidence.observations)
   simulation_engine.reset();self._baseline();runtime_service.measure(SensorWindowRequest());scenario_provider.select(ScenarioType.SLOW_UNILATERAL_SHIFT, __import__('app.domain.enums',fromlist=['ArmSide']).ArmSide.LEFT);scenario_provider.start()
   for _ in range(3):simulation_engine.step(2*86400);runtime_service.measure(SensorWindowRequest())
   persistent=decision_service.latest().surveillance_state.value;scenario_provider.reset();simulation_engine.step(86400);recovered=runtime_service.measure(SensorWindowRequest()).current_surveillance_state
   check(s,'longitudinal.recovery','Future observations permit recovery',True,persistent=='PERSISTENT_DEVIATION' and recovered=='WITHIN_PERSONAL_BASELINE',{'before':persistent,'after_observation':recovered})
   summary={'slow_left':arms['left_run'],'slow_right':arms['right_run'],'systemic':systemic.observed_evidence.observations,'transient':transient.observed_evidence.observations,'recovery':{'before':persistent,'after':recovered}}

   s=section('model_failure','Safe model failure behavior');before=ml_runtime._interpreter;missing=challenge_service.run('model-unavailable');check(s,'model_failure.unavailable','Missing model produces no fake downstream output',True,missing.status.value=='PASS',missing.observed_evidence.model_dump(mode='json'));check(s,'model_failure.restored','Normal interpreter restored',True,ml_runtime._interpreter is before,{'restored':ml_runtime._interpreter is before})
   with tempfile.TemporaryDirectory() as temp:
    directory=Path(temp);(directory/f'{MODEL_REVISION}-int8.tflite').write_bytes(artifact.read_bytes());bad=dict(meta);bad['artifacts']=dict(meta['artifacts']);bad['artifacts']['int8_sha256']='0'*64;(directory/f'{MODEL_REVISION}.metadata.json').write_text(json.dumps(bad))
    with patch('app.ml.runtime.MODEL_DIR',directory):isolated=MLRuntime();loaded=isolated.load()
   check(s,'model_failure.hash','Isolated hash mismatch rejected',True,not loaded and 'SHA256 mismatch' in (isolated.error or ''),{'loaded':loaded,'error':isolated.error,'committed_artifact_modified':False})

   s=section('boundaries','Anti-leakage and product boundaries');leak=challenge_service.run('label-leakage');check(s,'boundaries.leakage','Scenario/challenge fields absent from intelligence contracts',True,leak.status.value=='PASS',leak.observed_evidence.observations)
   forbidden_patient={'bis_sweep','r_zero_ohm','tflite','ewma_novelty','cusum_value','scenario_type','diagnosis','risk_percentage'};patient=client.get('/api/v1/views/patient').json();clinician=client.get('/api/v1/views/clinician').json();check(s,'boundaries.patient','Patient projection is minimized',True,forbidden_patient.isdisjoint(self._keys(patient)),{'keys':sorted(self._keys(patient))});check(s,'boundaries.clinician','Clinician projection remains scenario-blind',True,{'scenario_type','scenario_id','severity','disease_probability','diagnosis'}.isdisjoint(self._keys(clinician)),{'keys':sorted(self._keys(clinician))});lab=client.get('/api/v1/views/lab').json();digital=client.get('/api/v1/views/digital-twin').json();check(s,'boundaries.engineering','Ground truth limited to designed engineering views',True,'scenario_type' in self._keys(lab) and 'scenario_type' in self._keys(digital),{'lab_truth':True,'digital_twin_truth':True})

   s=section('stale_replay','Stale-cycle and replay integrity');stale=challenge_service.run('stale-decision');check(s,'stale.cycle','Rejected cycle does not inherit AI output',True,stale.status.value=='PASS',stale.observed_evidence.observations)
   simulation_engine.reset();client.post('/api/v1/scenarios/select',json={'scenario_type':'SLOW_UNILATERAL_SHIFT','affected_arm':'LEFT'});client.post('/api/v1/scenarios/start');client.post('/api/v1/simulation/step',json={'seconds':172800});client.post('/api/v1/runtime/measure',json={'motion_condition':'ACTIVE_MOTION','contact_condition':'NOMINAL_CONTACT'});timeline=client.get('/api/v1/views/timeline').json();observer=client.get('/api/v1/views/timeline?include_ground_truth=false').json();seq=[x['sequence_index'] for x in timeline['events']];check(s,'replay.order','Timeline events append in order',True,seq==sorted(seq),{'sequence':seq});rejected=[x for x in timeline['events'] if x['event_type']=='MEASUREMENT_REJECTED'];check(s,'replay.rejected','Rejected replay event has no fake AI',True,bool(rejected) and all(x['ml_summary'] is None and x['decision_summary'] is None for x in rejected),{'rejected_count':len(rejected)});check(s,'replay.observer','Observer replay strips ground truth',True,all(x['scenario_ground_truth'] is None and x['source']!='SCENARIO_ENGINE' for x in observer['events']),{'events':len(observer['events'])})

   s=section('privacy_adversarial','Privacy consistency and adversarial suite');privacy=client.get('/api/v1/views/privacy').json();check(s,'privacy.local','Privacy DTO reports local INT8 inference',True,privacy['model_execution']['loaded'] and privacy['model_execution']['execution_location']=='LOCAL PROTOTYPE PROCESS',privacy['model_execution']);check(s,'privacy.cloud','Privacy DTO reports no cloud/model API',True,not privacy['network_dependencies']['cloud_inference_required'] and not privacy['network_dependencies']['external_model_api_required'],privacy['network_dependencies']);check(s,'privacy.future','Hardware deployment explicitly future',True,privacy['planned_hardware_deployment']['status'].startswith('FUTURE / TARGET'),privacy['planned_hardware_deployment'])
   scan='\n'.join(path.read_text(errors='ignore') for base in (ROOT/'backend/app',ROOT/'frontend',ROOT/'docs') for pattern in ('*.py','*.tsx','*.md') for path in base.rglob(pattern) if '.next' not in path.parts and 'verification' not in path.parts).lower();normalized=scan.replace('not clinically validated','').replace('no clinical data','')
   unsupported=[phrase for phrase in ('hipaa compliant','gdpr certified','fda approved','clinically validated','disease probability:') if phrase in normalized];check(s,'privacy.copy','No unsupported positive claims',True,not unsupported,{'matches':unsupported})
   suite=challenge_service.run_all();critical_ids={'active-motion','model-unavailable','label-leakage','scenario-reset','stale-decision'};critical_ok=all(x.status.value=='PASS' for x in suite if x.challenge_id in critical_ids);check(s,'adversarial.critical','Critical adversarial invariants pass',True,critical_ok,{'results':{x.challenge_id:x.status.value for x in suite}});noncritical_fail=[x.challenge_id for x in suite if x.challenge_id not in critical_ids and x.status.value=='FAIL'];check(s,'adversarial.noncritical','Noncritical adversarial outcomes recorded',False,not noncritical_fail,{'results':{x.challenge_id:x.status.value for x in suite}},warning=bool(noncritical_fail))

   s=section('api_frontend','API, WebSocket, and frontend routes');routes=['/health','/api/v1/system/status','/api/v1/runtime/status','/api/v1/views/patient','/api/v1/views/clinician','/api/v1/views/engineering','/api/v1/views/lab','/api/v1/views/digital-twin','/api/v1/views/timeline','/api/v1/views/privacy','/api/v1/challenges','/api/v1/demo/status']
   for route in routes:
    response=client.get(route);check(s,'api.'+route.strip('/').replace('/','.'),f'API smoke {route}',True,response.status_code==200,{'status_code':response.status_code})
   simulation_engine.reset()
   with client.websocket_connect('/ws/runtime') as ws:
    initial=ws.receive_json();runtime_service.measure(SensorWindowRequest());update=ws.receive_json()
   check(s,'websocket.runtime','Runtime WebSocket connects and publishes cycle update',True,initial['type']=='runtime.snapshot' and update['snapshot'] is not None,{'initial_cycle':initial['snapshot'],'updated_cycle':update['snapshot']['cycle_id']})
   frontend_routes=['','patient','clinician','engineering','lab','digital-twin','timeline','privacy','challenge']
   if (ROOT/'frontend/app/demo/page.tsx').exists():frontend_routes.append('demo')
   for route in frontend_routes:check(s,'frontend.'+(route or 'home'),f'Frontend route source /{route}',True,(ROOT/'frontend/app'/route/'page.tsx').exists() if route else (ROOT/'frontend/app/page.tsx').exists(),{'route':'/'+route})
   check(s,'frontend.build_config','Frontend package scripts available',True,all(x in json.loads((ROOT/'frontend/package.json').read_text())['scripts'] for x in ('lint','typecheck','build')),{'scripts':json.loads((ROOT/'frontend/package.json').read_text())['scripts']})
  except Exception as error:
   s=section('runner_error','Verifier internal error');check(s,'runner.internal','Verification runner completed',True,False,{'error':repr(error)},reason=str(error))
  finally:simulation_engine.reset()
  checks=[c for sec in sections for c in sec.checks];finished=datetime.now(timezone.utc)
  for c in checks:c.duration_ms=round((finished-started).total_seconds()*1000/max(1,len(checks)),3)
  try:commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=False).stdout.strip() or None
  except OSError:commit=None
  report=VerificationReport(release_verification_revision=REVISION,started_at=started,finished_at=finished,git_commit=commit,model_hash=digest if 'digest' in locals() else None,total_checks=len(checks),passed=sum(x.status is VerificationStatus.PASS for x in checks),failed=sum(x.status is VerificationStatus.FAIL for x in checks),warnings=sum(x.status is VerificationStatus.WARNING for x in checks),skipped=sum(x.status is VerificationStatus.SKIPPED for x in checks),overall_status=overall_for(checks),sections=sections,scenario_summary=summary,known_warnings=['Synthetic sensing is not clinical or hardware validation.','Security controls remain prototype-only.'])
  self._latest=report
  if write_reports:self._write(report)
  return report
 def _write(self,report):
  OUTPUT_DIR.mkdir(exist_ok=True);(OUTPUT_DIR/'latest-verification.json').write_text(report.model_dump_json(indent=2),encoding='utf-8')
  lines=[f'# Aequor Release Verification','',f'**Status:** {report.overall_status.value}',f'**Revision:** {report.release_verification_revision}',f'**Checks:** {report.passed} passed, {report.failed} failed, {report.warnings} warnings, {report.skipped} skipped','']
  for section in report.sections:
   lines.extend([f'## {section.title}','']);lines.extend(f'- **{x.status.value}** `{x.check_id}` — {x.title}'+(f': {x.failure_reason}' if x.failure_reason else '') for x in section.checks);lines.append('')
  lines.extend(['## Known limitations','',*['- '+x for x in report.known_warnings]])
  (OUTPUT_DIR/'latest-verification.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 def latest(self):
  if self._latest:return self._latest
  path=OUTPUT_DIR/'latest-verification.json'
  return VerificationReport.model_validate_json(path.read_text()) if path.exists() else None


verification_service=ReleaseVerificationService()
