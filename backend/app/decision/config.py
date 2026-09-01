WEIGHTS={'personalized_deviation':.25,'ml_novelty':.20,'temporal':.35,'unilateral_pattern':.20}; TOP_K=6; CLIP=8.0
OBSERVE=25.; PERSISTENT=50.; REVIEW=65.; EXIT_OBSERVE=18.; EXIT_PERSISTENT=40.; MIN_REVIEW_DAYS=5.; MIN_REVIEW_COUNT=5
def public_config(): return {'decision_engine_name':'Aequor Surveillance Decision Engine','adi_revision':'adi-v1','state_machine_revision':'surveillance-v1','weights':WEIGHTS,'top_k':TOP_K,'thresholds':{'observe':OBSERVE,'persistent':PERSISTENT,'review':REVIEW},'all_thresholds_are':'PROTOTYPE ENGINEERING PARAMETERS'}
