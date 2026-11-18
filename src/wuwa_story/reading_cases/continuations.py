"""Apply task-specific additions once their source evidence is available."""
from .avinuolin import add_battle_aftermath
from .camp import add_camp_conversation
from .chengxiao import add_final_seal_dialogue
from .courtyard import add_library_confrontation
from .echoes import add_isle_dialogue
from .old_house import add_old_house_awakening
from .ruins import add_ruins_battle_report
from .whispering_town import add_town_investigation


def add_recap_continuations(quest, nodes, backbone, states, source, choices):
    add_battle_aftermath(quest, nodes, backbone, states, source, choices)
    add_final_seal_dialogue(quest, backbone, states, source, choices)
    add_library_confrontation(quest, nodes, backbone, states, source, choices)
    add_old_house_awakening(quest, nodes, backbone, states, source, choices)


def add_owned_continuations(quest, nodes, backbone, states, source, choices,
                            levelplay_links, levelplay_audits, entity_links):
    add_isle_dialogue(quest, nodes, backbone, states, source, choices, levelplay_links, levelplay_audits)
    add_ruins_battle_report(quest, nodes, backbone, states, source, choices, levelplay_links, levelplay_audits)
    add_town_investigation(quest, nodes, backbone, states, source, choices, levelplay_links, levelplay_audits)
    add_camp_conversation(quest, nodes, backbone, states, source, choices, entity_links)
