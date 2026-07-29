from psychopy import core, event, visual, gui
from function.config import settings as cfg



# ─────────────────────────────────────────────────────────────────────────────
# 0. Subject info dialog
# ─────────────────────────────────────────────────────────────────────────────

def get_subject_info():
    dlg = gui.Dlg(title="Chinese Character Experiment")
    dlg.addField("Subject ID:", "001")
    dlg.addField("Session:",    "1")
    data = dlg.show()
    if not dlg.OK:
        core.quit()
    return {
        "subject_id": data[0].strip(),
        "session":    data[1].strip(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. Instructions screen helper
# ─────────────────────────────────────────────────────────────────────────────

def show_instructions(win, text: str):
    event.clearEvents()
    msg = visual.TextStim(
        win,
        text=text,
        font=cfg.FONT,
        pos=(0, 0),
        height=42,
        color="white",
        wrapWidth=1400,
        bold=True,
    )
    msg.draw()
    win.flip()
    event.waitKeys(keyList=["space"])   # press space to continue
    event.clearEvents()
