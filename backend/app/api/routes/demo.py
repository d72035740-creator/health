from fastapi import APIRouter,HTTPException
from app.demo.models import CompetitionDemoSnapshot
from app.demo.service import DemoError,demo_service

router=APIRouter(prefix='/api/v1/demo',tags=['competition-demo'])
@router.get('/status',response_model=CompetitionDemoSnapshot)
async def status():return demo_service.snapshot()
def perform(action):
 try:return action()
 except DemoError as error:raise HTTPException(status_code=409,detail=str(error)) from error
@router.post('/reset',response_model=CompetitionDemoSnapshot)
async def reset():return perform(demo_service.reset)
@router.post('/baseline',response_model=CompetitionDemoSnapshot)
async def baseline():return perform(demo_service.establish_baseline)
@router.post('/stable',response_model=CompetitionDemoSnapshot)
async def stable():return perform(demo_service.verify_stable)
@router.post('/slow-left',response_model=CompetitionDemoSnapshot)
async def slow_left():return perform(demo_service.run_slow_left)
@router.post('/start-slow-left',response_model=CompetitionDemoSnapshot)
async def start_slow_left():return perform(demo_service.start_slow_left)
@router.post('/checkpoint',response_model=CompetitionDemoSnapshot)
async def checkpoint():return perform(demo_service.next_checkpoint)
