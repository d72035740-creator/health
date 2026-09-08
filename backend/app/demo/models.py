from pydantic import AwareDatetime
from app.domain.models import ContractModel


class DemoTrendPoint(ContractModel):
    simulated_time:AwareDatetime;left_relative_pattern:float|None;right_relative_pattern:float|None;novelty_z:float|None;ewma:float|None;adi:float|None;surveillance_state:str
class CompetitionDemoSnapshot(ContractModel):
    title:str;step_index:int;total_steps:int;step_title:str;busy:bool;baseline:dict[str,object];scenario_ground_truth:dict[str,object];observed:dict[str,object]|None;trend:list[DemoTrendPoint];runtime_cycle_ids:list[str];disclosure:str;automation_boundary:str
    checkpoint_index:int=0;total_checkpoints:int=3;active_experiment:str|None=None;latest_pipeline:list[dict[str,object]]|None=None;patient_preview:dict[str,object]|None=None;clinician_preview:dict[str,object]|None=None
