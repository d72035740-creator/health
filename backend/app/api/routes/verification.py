from fastapi import APIRouter,HTTPException
from app.verification.models import VerificationReport
from app.verification.service import verification_service

router=APIRouter(prefix='/api/v1/verification',tags=['release-verification'])
@router.get('/latest',response_model=VerificationReport)
async def latest():
 report=verification_service.latest()
 if report is None:raise HTTPException(status_code=404,detail='No release verification report has been generated.')
 return report
