import math
from app.domain.models import BioimpedanceSweep
from app.signal_processing.models import ColeFitResult

def _predict(f:float,r0:float,rinf:float,tau:float,beta:float)->complex:
    return rinf+(r0-rinf)/(1+(1j*2*math.pi*f*tau)**beta)

def fit_cole(sweep:BioimpedanceSweep)->ColeFitResult:
    observed=[complex(p.resistance_ohm,p.reactance_ohm) for p in sweep.points]
    try:
        lo=min(p.magnitude_ohm for p in sweep.points); hi=max(p.magnitude_ohm for p in sweep.points)
        if not math.isfinite(lo+hi) or lo<=0: raise ValueError("invalid observed range")
        # Deterministic bounded coordinate descent; only acquired R/X values are used.
        params=[hi*1.15,max(lo*.75,1e-3),1e-4,.75]; bounds=[(lo,hi*3),(1e-6,hi*2),(1e-7,.1),(.05,1.0)]
        def err(q): return math.sqrt(sum(abs(_predict(p.frequency_hz,*q)-z)**2 for p,z in zip(sweep.points,observed))/len(observed))
        steps=[(hi-lo)*.25,max(hi-lo,.1)*.2,1e-4,.2]; best=err(params)
        for _ in range(28):
            changed=False
            for i in range(4):
                candidates=[]
                for sign in (-1,1):
                    q=params.copy(); q[i]=min(bounds[i][1],max(bounds[i][0],q[i]+sign*steps[i])); candidates.append((err(q),q))
                score,q=min(candidates,key=lambda item:item[0])
                if score<best: best,params,changed=score,q,True
                else: steps[i]*=.5
            if not changed and max(steps)<1e-8: break
        r0,rinf,tau,beta=params
        if not (r0>rinf>0 and tau>0 and 0<beta<=1 and math.isfinite(best)): raise ValueError("bounded fit failed")
        return ColeFitResult(fit_success=True,r0_ohm=r0,rinf_ohm=rinf,tau_seconds=tau,beta=beta,complex_rmse_ohm=best)
    except (ValueError,ZeroDivisionError,OverflowError) as error:
        return ColeFitResult(fit_success=False,failure_reason=str(error))
