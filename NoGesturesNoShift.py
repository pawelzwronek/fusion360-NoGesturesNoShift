# Author - pawelzwronek
# Description - Disables gestures so you can use RMB to orbit the viewport

# Changelog
# v1.0 - Initial version
# v1.0.1 - fix GetKeyState() on Win7
# v1.2 - build for python 3.7
# v1.3 - fix for Fusion360 v2.0.8609 - June 2020 Update
# v1.5 - fix for Fusion360 v2.0.10027 - April 2021 Update
# v1.6 - fix for Fusion360 2.0.12665 - March 2022 Update
# v1.7 - fix for Fusion360 2.0.17244 - September 2023 Update
#      - python changed to 3.11
# v1.8 - fix for Fusion360 2.0.20256
#      - python changed to 3.12
#      - update SWIG to v4.2.0
# v2.0 - fix hung up on rapid RMB clicks
#      - better RMB response
#      - pure python implementation, no SWIG binaries

import math
import threading
import subprocess
import os
import sys
import datetime
import traceback
import tkinter as tk
import time

# pylint: disable=W0603

logToFile = False
logToConsole = False

rmbAsOrbit = True

boot = 'boot'
if len(sys.argv) > 1:
    boot = 'main'

print(boot)

# Logfile
_tmpPath =None

pid = os.getpid()

def log(msg):
    global _tmpPath
    if logToFile or logToConsole:
        fracSecs = time.time()
        fracSecs = int((fracSecs - int(fracSecs))*1000)
        msg = f"{datetime.datetime.now().strftime(f'%Y-%m-%d %H:%M:%S.{fracSecs:03}')} {boot}({pid}): {msg}"
        if logToConsole:
            print(msg, flush=True)
        if logToFile:
            if not _tmpPath:
                import tempfile # pylint: disable=C0415
                with tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='NoGestures_', suffix='.log') as tmpFile:
                    if tmpFile and tmpFile.file and tmpFile.name:
                        _tmpPath = tmpFile.name
            if _tmpPath:
                with open(_tmpPath, 'a', encoding='utf-8') as f:
                    f.write(msg + '\n')

fromFusion = __name__ != '__main__'
log('fromFusion: ' + str(fromFusion))

# find Fusion python interpreter
pyt = os.path.join(os.path.split(tk.__file__)[0], '..\\..\\python')
log('exe: ' + pyt)

# if executed directly from Fusion run this script as a subprocess to avoid
# lags in mouse events coused by Fusion's python loop
process = None
if len(sys.argv) == 1:
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW | subprocess.CREATE_NEW_PROCESS_GROUP  # hide console window
    log('running subprocess: ' + pyt + ' ' + __file__ + ' main')
    process = subprocess.Popen(pyt + ' ' + __file__ + ' main', startupinfo=si)


try:
    if fromFusion:
        from . import autohotkey as ahk
    else:
        import autohotkey as ahk
except ImportError as ex:
    log(traceback.format_exc())

# ==================================+++++++++++++++++===================================================================
# ==================================   main script   ===================================================================

def fire_in(func, time_ms, ars=None):
    log('fire in ' + str(time_ms) + ' ' + str(func.__name__) + '(' + str(ars) + ')')
    threading.Timer(time_ms/1000, func, args=ars).start()

xpos = 0
ypos = 0
xpos2 = 0
ypos2 = 0
detecting_move = False
move_detected = False
inFusion = False
rbutton_down = False
shift_pressed = False


def is_in_fusion():
    className = str(ahk.getClassUnderMouse())
    log('className: ' + className)
    return 'QWindowIcon:Fusion360' in className or 'AcApCoreView' in className


def detect_move(start=-1):
    global xpos, ypos, xpos2, ypos2, detecting_move, move_detected
    if isinstance(start, bool) and start:
        detecting_move = True
        move_detected = False
        xpos, ypos = ahk.GetCursorPos()
        fire_in(detect_move, 100)
    elif isinstance(start, bool) and not start:
        detecting_move = False
    elif detecting_move:
        xpos2, ypos2 = ahk.GetCursorPos()
        distance = math.floor(math.sqrt((ypos2-ypos)**2 + (xpos-xpos2)**2) + 0.5)
        if distance > 5:
            move_detected = True
            log('move detected')
            detecting_move = False
        else:
            fire_in(detect_move, 100)


def RButton(event):
    global rbutton_down, shift_pressed
    try:
        if not event.Injected:
            if is_in_fusion():
                log('rdown inFusion')
                rbutton_down = True
                fire_in(ahk.MDown, 1)
                detect_move(True)
                shift_pressed = ahk.GetKeyState('VK_LSHIFT')
                if rmbAsOrbit:
                    if not shift_pressed:
                        ahk.SetKeyState('VK_LSHIFT', True) # press SHIFT key
                    else:
                        ahk.block_mouse_move(True)
                        fire_in(ahk.MUp, 100)
                        fire_in(ahk.block_mouse_move, 120, {False})
                return False  # block event
            else:
                log('rdown ')
    except Exception: # pylint: disable=W0703
        log(traceback.format_exc())
    return True  # pass event to next hook


def RButtonup(event):
    global rbutton_down
    try:
        if not event.Injected:
            if rbutton_down:
                log('rup')
                rbutton_down = False
                detect_move(False)
                if rmbAsOrbit:
                    ahk.SetKeyState('VK_LSHIFT', False) # release SHIFT key

                if not move_detected:
                    if not rmbAsOrbit and shift_pressed:
                        log('no move, shift')
                        ahk.block_mouse_move(True)
                        fire_in(ahk.MUp, 10)
                        fire_in(ahk.block_mouse_move, 100, {False})
                    elif not shift_pressed:
                        log('no move, no shift')
                        ahk.block_mouse_move(True)
                        fire_in(ahk.MUp, 0)
                        fire_in(ahk.RDown, 10)
                        fire_in(ahk.RUp, 100)
                        fire_in(ahk.block_mouse_move, 300, {False})
                else:
                    fire_in(ahk.MUp, 50)

                return False  # block event
    except Exception: # pylint: disable=W0703
        log(traceback.format_exc())
    return True  # pass event to next hook

ui = None
try:
    if process is None:
        log('hook RMB')
        ahk.setOnRButton(RButton)
        ahk.setOnRButtonUp(RButtonup)
        ahk.hookMouse()

        # start hiddent Tk window to pump event
        root = tk.Tk()
        root.withdraw()
        log('mainloop starting...')
        root.mainloop()
        log('mainloop ended')
except Exception: # pylint: disable=W0703
    log(traceback.format_exc())


# fusion callback
def run(_context):
    log('run')
    if process is not None:
        log('bootstrap')


def process_terminate():
    process.terminate()

# fusion callback
def stop(_context):
    log('stop')
    if ui is not None:
        ui.messageBox('stop')
    if process is not None:
        log(f'kill {process.pid}')
        fire_in(process_terminate, 1)
        time.sleep(0.1)
        log('process killed')


if not fromFusion and boot == 'boot':
    run(None)
    root = tk.Tk()
    root.mainloop()
    log('mainloop started')
    stop(None)

log('end of script')
