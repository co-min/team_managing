from psychopy import event, visual, core


def check_escape(win: visual.Window) -> None:
    if event.getKeys(keyList=["escape"]):
        win.close()
        core.quit()
