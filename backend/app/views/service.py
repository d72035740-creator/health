from app.views.models import *
from app.runtime import runtime_service
from app.baseline.service import baseline_service
from app.decision.service import decision_service
from app.simulation.engine import simulation_engine
from app.quality.models import MeasurementQualification
from app.ml.runtime import ml_runtime
from app.temporal.service import temporal_service
from app.decision.config import public_config as decision_config
from app.scenario import scenario_provider
from app.api.routes.system import system_status
from app.domain.enums import ArmSide
from app.simulation.bioimpedance.cole import ColeImpedanceModel
from app.simulation.bioimpedance.config import DEFAULT_FREQUENCIES, LEFT_ARM_PARAMETERS, RIGHT_ARM_PARAMETERS
from math import atan2, degrees, sqrt
from app.timeline.service import timeline_service

COPY={
'CALIBRATING':('Learning your personal reference','Aequor is collecting qualified measurements to learn your normal bilateral pattern.'),
'WITHIN_PERSONAL_BASELINE':('Within your personal reference','Your recent bilateral pattern remains close to the reference Aequor has learned for you.'),
'OBSERVING_CHANGE':('A small change is being observed','Aequor has noticed a change from your personal reference and is continuing to monitor whether it persists.'),
'PERSISTENT_DEVIATION':('A persistent change has been observed','The change from your personal reference has continued across multiple qualified measurements.'),
'CLINICAL_REVIEW_RECOMMENDED':('Consider discussing this trend with your care team','A persistent change from your personal reference has been observed across multiple measurements. This is not a diagnosis.')}

def _relative(attempt):
    if not attempt or not attempt.baseline_comparison:return None
    values={v.name:v.signed_normalized_delta for v in attempt.baseline_comparison.values}; left=[v for k,v in values.items() if k.startswith('left_')]; right=[v for k,v in values.items() if k.startswith('right_')]
    l=100+(sum(left)/len(left) if left else 0); r=100+(sum(right)/len(right) if right else 0); return round(l,1),round(r,1)
class PatientViewService:
 def snapshot(self):
    sim=simulation_engine.snapshot(); base=baseline_service.snapshot(); latest=runtime_service.snapshot(); decision=decision_service.latest(); state=decision.surveillance_state.value if decision else 'CALIBRATING'; title,message=COPY[state]; history=runtime_service.history(); qualified=[x for x in history if x.attempt.quality_assessment.qualification is MeasurementQualification.QUALIFIED]; rejected=len(history)-len(qualified); rel=_relative(latest.attempt if latest else None); trend=[]
    for x in qualified[-14:]:
      rr=_relative(x.attempt)
      if rr: trend.append(PatientTrendPoint(simulated_time=x.simulated_time,relative_balance_value=round(abs(rr[0]-rr[1]),2)))
    progress=min(100,round(100*min(base.observation_count/base.minimum_observations,base.simulated_span_seconds/base.minimum_simulated_span_seconds),1)) if base.minimum_observations and base.minimum_simulated_span_seconds else 0
    latest_view=None
    if latest: latest_view={'simulated_time':latest.simulated_time,'technical_quality_label':'Not used — sensing conditions were not stable' if latest.pipeline_status.value=='BLOCKED_BY_QUALITY' else 'Excellent measurement quality' if latest.attempt.quality_assessment.overall_score>=90 else 'Good measurement quality','updated_surveillance_state':latest.cycle_decision_updated,'pipeline_status':latest.pipeline_status.value}
    return PatientViewSnapshot(synthetic_patient={'display_name':sim.patient.display_name,'patient_id':sim.patient.patient_id,'synthetic':True},prototype_disclosure='Prototype demo using simulated physiological sensing.',surveillance_state=state,state_title=title,state_message=message,baseline={'state':base.state.value,'calibration_progress_percent':progress,'qualified_observations':base.observation_count,'required_observations':base.minimum_observations,'simulated_span_days':round(base.simulated_span_seconds/86400,1),'required_span_days':round(base.minimum_simulated_span_seconds/86400,1)},latest_measurement=latest_view,fluid_balance_summary={'left_relative_index':rel[0],'right_relative_index':rel[1],'bilateral_pattern_difference':round(abs(rel[0]-rel[1]),1),'trend_direction':'DIVERGING' if abs(rel[0]-rel[1])>2 else 'STABLE'} if rel else None,trend=trend,measurement_summary=PatientMeasurementSummary(total_recent_attempts=len(history),qualified_recent_attempts=len(qualified),rejected_recent_attempts=rejected),privacy_summary={'processing':'On device / local prototype process','raw_data':'Kept within the Aequor processing environment','cloud_inference':'Not required'},recommended_message='Continue your regular measurement routine.' if state!='CLINICAL_REVIEW_RECOMMENDED' else 'Consider discussing this longitudinal trend with your care team. This is not a diagnosis.')
class ClinicianViewService:
 def snapshot(self):
    patient=simulation_engine.snapshot().patient; base=baseline_service.snapshot(); latest=runtime_service.snapshot(); decision=decision_service.latest(); attempt=latest.attempt if latest else None; rel=_relative(attempt); history=runtime_service.history(); trend=[]
    for x in history[-30:]:
      rr=_relative(x.attempt)
      if rr: trend.append(ClinicianTrendPoint(simulated_time=x.simulated_time,left_relative_index=rr[0],right_relative_index=rr[1],adi=x.attempt.decision_snapshot.adi if x.attempt.decision_snapshot else None,surveillance_state=x.attempt.decision_snapshot.surveillance_state.value if x.attempt.decision_snapshot else None))
    spectrum=[]
    if attempt and attempt.bis_sweep:
      for l,r in zip(attempt.bis_sweep.left.points,attempt.bis_sweep.right.points,strict=True): spectrum.append({'frequency_hz':l.frequency_hz,'left_magnitude_ohm':round(l.magnitude_ohm,2),'right_magnitude_ohm':round(r.magnitude_ohm,2),'difference_ohm':round(l.magnitude_ohm-r.magnitude_ohm,2)})
    temporal=attempt.temporal_assessment if attempt else None; conf=attempt.confounder_assessment if attempt else None
    return ClinicianViewSnapshot(patient={'display_name':patient.display_name,'patient_id':patient.patient_id,'synthetic':True},prototype_disclosure='Engineering prototype — measurements shown are generated by the Aequor digital twin and are not clinical patient data.',surveillance_state=decision.surveillance_state.value if decision else 'CALIBRATING',adi=decision.adi if decision else None,adi_label='Prototype research index — not disease probability',adi_revision=decision.adi_revision if decision else 'adi-v1',dominant_observed_side=decision.dominant_observed_side if decision else None,latest_measurement={'simulated_time':latest.simulated_time,'pipeline_status':latest.pipeline_status.value,'updated_decision':latest.cycle_decision_updated,'state_last_updated':latest.last_decision_time} if latest else None,quality_summary={'latest_score':attempt.quality_assessment.overall_score if attempt else None,'qualified_recent':sum(x.attempt.quality_assessment.qualification is MeasurementQualification.QUALIFIED for x in history),'rejected_recent':sum(x.attempt.quality_assessment.qualification is MeasurementQualification.REJECTED for x in history)},bilateral_summary={'left_relative_index':rel[0],'right_relative_index':rel[1],'observed_pattern_difference':round(abs(rel[0]-rel[1]),1)} if rel else None,spectral_summary=spectrum,baseline_summary={'state':base.state.value,'observations':base.observation_count,'span_days':round(base.simulated_span_seconds/86400,1),'feature_revision':base.feature_revision,'baseline_revision':base.baseline_revision},temporal_summary=temporal.model_dump(mode='json') if temporal else None,confounder_summary=conf.model_dump(mode='json') if conf else None,decision_components=decision.components if decision else None,decision_modifiers=decision.modifiers if decision else None,explanations=decision.explanations if decision else [],longitudinal_trend=trend,state_history=[{'simulated_time':x.simulated_time,'state':x.surveillance_state.value,'adi':x.adi} for x in decision_service.history()],model_metadata_summary={'model':'Aequor Tiny Autoencoder','runtime':'TFLite INT8','inference':'Local','model_revision':'aequor-ae-v1','input':'Personalized baseline-relative features'})
patient_view_service=PatientViewService();clinician_view_service=ClinicianViewService()

class EngineeringViewService:
 def snapshot(self):
    sim=simulation_engine.snapshot(); latest=runtime_service.snapshot(); attempt=latest.attempt if latest else None; base=baseline_service.snapshot(); decision=decision_service.latest(); ml=ml_runtime.status()
    stage_status={x:'NOT_RUN' for x in ('SENSORS','QUALITY','BIS','FEATURES','BASELINE','TINYML','TEMPORAL','CONFOUNDERS','DECISION')}
    if latest:
      for event in latest.pipeline_events: stage_status[event.stage]='BLOCKED' if event.status=='REJECTED' else event.status
      if latest.pipeline_status.value=='BLOCKED_BY_QUALITY': stage_status['QUALITY']='BLOCKED'
    pipeline=[{'stage':x,'status':stage_status[x]} for x in stage_status]
    bis=None
    if attempt and attempt.bis_sweep: bis={'provenance':'SIMULATED','left':[p.model_dump(mode='json') for p in attempt.bis_sweep.left.points],'right':[p.model_dump(mode='json') for p in attempt.bis_sweep.right.points]}
    quality=attempt.quality_assessment if attempt else None; features=attempt.processed_features if attempt else None; temporal=attempt.temporal_assessment if attempt else None; conf=attempt.confounder_assessment if attempt else None
    return EngineeringViewSnapshot(header={'patient':sim.patient.display_name,'simulated_time':sim.simulated_time,'runtime_status':runtime_service.status(),'surveillance_state':decision.surveillance_state.value if decision else 'CALIBRATING','latest_cycle':latest.cycle_index if latest else None,'decision_last_updated':decision.simulated_time if decision else None,'label':'PROTOTYPE / ENGINEERING'},pipeline=pipeline,latest_cycle={'cycle_index':latest.cycle_index,'simulated_time':latest.simulated_time,'pipeline_status':latest.pipeline_status.value,'quality_result':attempt.quality_assessment.qualification.value,'decision_updated':latest.cycle_decision_updated,'rejection_codes':[x.value for x in attempt.quality_assessment.rejection_reasons],'current_surveillance_state':latest.current_surveillance_state,'last_decision_time':latest.last_decision_time} if latest else None,technical_acquisition={'qualification':quality.qualification.value,'overall_score':quality.overall_score,'dimension_scores':quality.dimension_scores.model_dump(),'rejection_codes':[x.value for x in quality.rejection_reasons]} if quality else None,bis=bis,signal_processing=features.model_dump(mode='json') if features else None,baseline=base.model_dump(mode='json'),tinyml={**ml,'inference':'LOCAL','cloud_calls':0,'input_dimension':34,'latest':attempt.ml_inference.model_dump(mode='json') if attempt and attempt.ml_inference else None,'required_copy':'PATTERN NOVELTY — NOT DISEASE PROBABILITY'},temporal=temporal.model_dump(mode='json') if temporal else None,temporal_history=[x.model_dump(mode='json') for x in temporal_service.history()],confounders=conf.model_dump(mode='json') if conf else None,decision=decision.model_dump(mode='json') if decision else None,adi_configuration=decision_config(),system_health={'digital_patient':'READY','bioimpedance':'READY','virtual_imu':'READY','temperature':'READY','contact':'READY','quality':'READY','signal_processing':'READY','baseline':'READY','scenario':'READY','ml':ml['status'],'temporal':'READY','confounder':'READY','decision':'READY','runtime':'READY'},provenance={'simulated_inputs':['physiology','bilateral BIS sensing','IMU','temperature','electrode contact'],'executable_software':['measurement quality gating','signal processing','personalized baseline learning','INT8 TFLite inference','temporal intelligence','confounder reasoning','ADI calculation','surveillance state machine','runtime orchestration']})

class LabViewService:
 def snapshot(self):
    sim=simulation_engine.snapshot(); scenario=scenario_provider.state(); base=baseline_service.snapshot(); latest=runtime_service.snapshot(); attempt=latest.attempt if latest else None; decision=decision_service.latest(); conf=attempt.confounder_assessment if attempt else None; temporal=attempt.temporal_assessment if attempt else None
    observed=None
    if attempt: observed={'technical_quality':attempt.quality_assessment.qualification.value,'quality_score':attempt.quality_assessment.overall_score,'bis_available':attempt.bis_sweep is not None,'novelty_z':attempt.ml_inference.novelty_z if attempt.ml_inference else None,'ewma':temporal.ewma_novelty if temporal else None,'cusum':temporal.cusum_value if temporal else None,'persistence_days':temporal.persistence_duration_days if temporal else None,'dominant_observed_side':conf.dominant_change_side.value if conf else None,'systemic_evidence':conf.systemic_bilateral_evidence if conf else None,'adi':attempt.decision_snapshot.adi if attempt.decision_snapshot else None,'surveillance_state':decision.surveillance_state.value if decision else 'CALIBRATING','decision_updated':latest.cycle_decision_updated}
    events=[]
    for x in runtime_service.history()[-12:]:
      events.append({'simulated_time':x.simulated_time,'event':'Measurement rejected' if x.pipeline_status.value=='BLOCKED_BY_QUALITY' else 'Measurement cycle completed','detail':x.pipeline_status.value})
      if x.attempt.decision_snapshot: events.append({'simulated_time':x.simulated_time,'event':'Decision updated','detail':x.attempt.decision_snapshot.surveillance_state.value})
    return LabViewSnapshot(simulation={'simulated_time':sim.simulated_time,'lifecycle':sim.lifecycle.value,'speed_multiplier':sim.speed_multiplier,'patient':sim.patient.display_name},scenario_ground_truth=scenario.as_dict(),baseline={'state':base.state.value,'observations':base.observation_count,'span_days':round(base.simulated_span_seconds/86400,2),'required_observations':base.minimum_observations,'required_span_days':round(base.minimum_simulated_span_seconds/86400,2)},runtime={'status':runtime_service.status(),'latest_pipeline_status':latest.pipeline_status.value if latest else None,'cycle_index':latest.cycle_index if latest else None},observed_evidence=observed,event_feed=events,disclosure='SYNTHETIC DIGITAL-TWIN GROUND TRUTH — ENGINEERING VIEW ONLY. The scenario engine modifies hidden synthetic physiology. The Aequor intelligence pipeline does not receive the scenario label.')

engineering_view_service=EngineeringViewService();lab_view_service=LabViewService()


def _parameter_values(parameters):
    return {"r_zero_ohm": parameters.r_zero_ohm, "r_infinity_ohm": parameters.r_infinity_ohm, "tau_seconds": parameters.tau_seconds, "beta": parameters.beta}


def _arm_parameter_view(arm, base, effective):
    return DigitalTwinArmParameters(
        arm=arm.value, base=_parameter_values(base), effective=_parameter_values(effective),
        modifier=DigitalTwinParameterModifier(
            delta_r_zero_ohm=effective.r_zero_ohm-base.r_zero_ohm,
            delta_r_infinity_ohm=effective.r_infinity_ohm-base.r_infinity_ohm,
            delta_tau_seconds=effective.tau_seconds-base.tau_seconds,
            delta_beta=effective.beta-base.beta))


def _spectrum(parameters):
    model=ColeImpedanceModel(parameters); result=[]
    for point in model.sweep(DEFAULT_FREQUENCIES.frequencies_hz):
        value=point.impedance_ohm
        result.append(DigitalTwinSpectrumPoint(frequency_hz=point.frequency_hz,resistance_ohm=value.real,reactance_ohm=value.imag,magnitude_ohm=abs(value),phase_deg=degrees(atan2(value.imag,value.real))))
    return result


class DigitalTwinInspectorService:
 def snapshot(self):
    now=simulation_engine.snapshot().simulated_time; state=scenario_provider.state()
    bases={ArmSide.LEFT:LEFT_ARM_PARAMETERS,ArmSide.RIGHT:RIGHT_ARM_PARAMETERS}
    effective={arm:scenario_provider.effective_parameters(arm,now,bases[arm]) for arm in bases}
    evolution=[DigitalTwinEvolutionPoint(progression=p,left=_parameter_values(scenario_provider.preview_parameters(ArmSide.LEFT,LEFT_ARM_PARAMETERS,p)),right=_parameter_values(scenario_provider.preview_parameters(ArmSide.RIGHT,RIGHT_ARM_PARAMETERS,p))) for p in (0.0,.25,.5,.75,1.0)]
    acquired_runtime=next((x for x in reversed(runtime_service.history()) if x.attempt.bis_sweep),None); acquired=None; comparisons=[]
    if acquired_runtime:
      attempt=acquired_runtime.attempt
      acquired={'measurement_attempt_id':attempt.attempt_id,'simulated_time':attempt.simulated_time,'noise_enabled':True,'left':[p.model_dump(mode='json') for p in attempt.bis_sweep.left.points],'right':[p.model_dump(mode='json') for p in attempt.bis_sweep.right.points]}
      features=attempt.processed_features
      for arm,truth,fitted in ((ArmSide.LEFT,effective[ArmSide.LEFT],features.left_cole_fit if features else None),(ArmSide.RIGHT,effective[ArmSide.RIGHT],features.right_cole_fit if features else None)):
       for label,truth_value,estimate in (("R0",truth.r_zero_ohm,fitted.r0_ohm if fitted else None),("R∞",truth.r_infinity_ohm,fitted.rinf_ohm if fitted else None),("τ",truth.tau_seconds,fitted.tau_seconds if fitted else None),("β",truth.beta,fitted.beta if fitted else None)):
        comparisons.append(DigitalTwinFitComparison(parameter=label,arm=arm.value,ground_truth_value=truth_value,processor_estimate=estimate,difference=estimate-truth_value if estimate is not None else None,fit_available=bool(fitted and fitted.fit_success)))
    latest=runtime_service.snapshot(); sensors=VirtualSensorInspectorSummary(available=False)
    if latest:
      attempt=latest.attempt; window=attempt.sensor_window; gravity={}; motion={}; temperatures={}; contacts={}; counts={}
      for arm_name,band in (("LEFT",window.left),("RIGHT",window.right)):
       n=len(band.imu_samples); ax=sum(x.acceleration_x_m_s2 for x in band.imu_samples)/n; ay=sum(x.acceleration_y_m_s2 for x in band.imu_samples)/n; az=sum(x.acceleration_z_m_s2 for x in band.imu_samples)/n
       gravity[arm_name]=sqrt(ax*ax+ay*ay+az*az)
       motion[arm_name]=sqrt(sum(x.angular_velocity_x_rad_s**2+x.angular_velocity_y_rad_s**2+x.angular_velocity_z_rad_s**2 for x in band.imu_samples)/n)
       temperatures[arm_name]=sum(x.temperature_c for x in band.temperature_samples)/len(band.temperature_samples)
       contacts[arm_name]=sum(x.contact_impedance_ohm for x in band.contact_samples)/len(band.contact_samples)
       counts[arm_name]={'imu':len(band.imu_samples),'temperature':len(band.temperature_samples),'contact':len(band.contact_samples)}
      quality=attempt.quality_assessment
      sensors=VirtualSensorInspectorSummary(available=True,motion_condition=window.motion_condition.value,posture_condition=window.motion_condition.value,gravity_projection_m_s2=gravity,motion_level_rad_s=motion,skin_temperature_c=temperatures,contact_impedance_ohm=contacts,technical_quality=quality.qualification.value,quality_score=quality.overall_score,technical_details={'window_id':window.window_id,'duration_seconds':window.duration_seconds,'sample_counts':counts,'rejection_reasons':[x.value for x in quality.rejection_reasons]})
    return DigitalTwinInspectorSnapshot(
      title='DIGITAL TWIN INSPECTOR',provenance_label='SYNTHETIC PHYSIOLOGY / ENGINEERING ONLY',
      disclosure="The digital twin generates controlled synthetic sensor data for testing Aequor's executable algorithms. These parameters are not clinical patient measurements.",
      equation={'cole':'Z(ω) = R∞ + (R0 - R∞) / (1 + (jωτ)^β)','angular_frequency':'ω = 2πf','r_zero':'R0: low-frequency resistance asymptote in the synthetic model','r_infinity':'R∞: high-frequency resistance asymptote in the synthetic model','tau':'τ: synthetic characteristic time constant','beta':'β: dimensionless synthetic dispersion exponent (0, 1]'},
      scenario_ground_truth={**state.as_dict(),'synthetic_progression':state.severity,'label':'GROUND TRUTH — NOT AN AEQUOR INFERENCE'},
      arm_parameters=[_arm_parameter_view(arm,bases[arm],effective[arm]) for arm in (ArmSide.LEFT,ArmSide.RIGHT)],parameter_evolution=evolution,
      model_prediction={'LEFT':_spectrum(effective[ArmSide.LEFT]),'RIGHT':_spectrum(effective[ArmSide.RIGHT])},latest_acquired_sweep=acquired,fit_comparison=comparisons,virtual_sensors=sensors,
      anti_leakage={'observed_path':['Hidden Ground Truth','Synthetic BIS','Acquired R/X values','Signal Processing','Estimated features'],'blocked_paths':['Hidden parameters ─X→ Signal processor','Scenario label ─X→ TinyML','Scenario severity ─X→ Decision Engine'],'statement':'Signal processing estimates these parameters from the acquired spectrum. It does not access the hidden digital-twin values.'},
      noise_explanation=['Deterministic acquisition noise exists.','Acquired spectra can differ slightly from the mathematical model curve.','Signal processing receives acquired observations, not hidden parameters.'])


digital_twin_inspector_service=DigitalTwinInspectorService()


class TimelineReplayViewService:
 def snapshot(self,include_ground_truth=True):
    decision=decision_service.latest()
    return timeline_service.projection(include_ground_truth=include_ground_truth,baseline_status=baseline_service.snapshot().state.value,current_state=decision.surveillance_state.value if decision else 'CALIBRATING')


timeline_replay_view_service=TimelineReplayViewService()
