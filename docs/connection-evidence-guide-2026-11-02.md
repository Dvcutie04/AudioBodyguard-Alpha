# Connection evidence guide — 2026-11-02

## Decision

Start the next connection-discovery increment by turning existing native output
metadata into one short, truthful next step. Keep detailed capabilities behind
the existing reviewed report. Do not add scanning, playback, microphone use,
device control, background polling or automatic connection claims.

This follows the research charter's progression of **observe → suggest → shadow
→ automate → suspend**. This increment remains at observe/suggest.

## User experience

After one explicit refresh, both platforms show:

1. one plain-language summary of what the phone reports;
2. one next action in the phone's native output controls;
3. **Connection not verified • No TV command sent**.

The technical explanation is behind a question-mark control. Android's main
screen shows only output kinds; sample rates, channels and encodings remain in
**Review output report**. iPhone keeps the immutable reviewed snapshot and adds
the same boundary to its report.

## Platform truth

- iPhone classifies only `AVAudioSession.currentRoute.outputs` port types. It
  never reads a port name or identifier and does not activate the session.
- Android classifies only the connected/available sink types returned by
  `AudioManager.getDevices(GET_DEVICES_OUTPUTS)`. Availability is not selection.
- Neither platform proves playback, a named TV identity, physical output,
  protection, authorization or command delivery.

## Research basis

- Apple defines `AVAudioSession.currentRoute` as the current route's input and
  output ports. The app reads only the output port types and deliberately omits
  names and identifiers:
  <https://developer.apple.com/documentation/avfaudio/avaudiosession/currentroute>
- Android defines `AudioDeviceInfo.getType()` as a device-type identifier. The
  app classifies only those coarse types, including BLE audio and HDMI eARC,
  while preserving the distinction between an available output and a selected
  playback route:
  <https://developer.android.com/reference/android/media/AudioDeviceInfo>

## Defaults and privacy

- No permission request.
- No network or Bluetooth discovery.
- No persistent device identifier or name.
- No automatic reread after a route/device notice; stale information is
  withdrawn and the user chooses when to refresh.
- Existing lifecycle clearing, bounded snapshots and reviewed sharing remain.

## Qualification still required

Simulator/emulator and unit tests can validate wording, classification,
lifecycle and the absence of hidden actuation. N2b physical qualification still
requires an owned phone plus a named TV/output endpoint, native instrumentation
and independent observation. A successful software test does not close that
gate.
