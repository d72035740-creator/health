from fastapi import APIRouter,HTTPException
from app.challenges.models import ChallengeDefinition,ChallengeResult,ChallengeSuiteSnapshot
from app.challenges.service import challenge_service

router=APIRouter(prefix='/api/v1/challenges',tags=['adversarial-challenges'])
@router.get('',response_model=list[ChallengeDefinition])
async def definitions():return challenge_service.definitions()
@router.get('/status',response_model=ChallengeSuiteSnapshot)
async def status():return challenge_service.snapshot()
@router.get('/history',response_model=list[ChallengeResult])
async def history():return challenge_service.history()
@router.post('/run-all',response_model=list[ChallengeResult])
async def run_all():return challenge_service.run_all()
@router.post('/{challenge_id}/run',response_model=ChallengeResult)
async def run(challenge_id:str):
 try:return challenge_service.run(challenge_id)
 except KeyError as error:raise HTTPException(status_code=404,detail='Unknown challenge') from error
