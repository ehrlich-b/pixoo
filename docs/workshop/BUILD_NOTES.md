# Mosslight Works — craft and verification log

Goal source: the user's attached enchanted-workshop brief (2026-09-05). The prior turn completed the project review, which is concrete progress; the worktree had no workshop implementation at the start of this goal turn.

Required result: a polished original single-display world; distinct two-display worlds with a character carrying an object between them and a visible destination consequence; engaging opening and varied persistent interactions; easy showcase controls; independent bounded device I/O at measured live cadence; local preview and recorded showcase; physical demonstration on explicitly selected devices if supplied; launch/stop instructions and regression checks.

## Visual directions, first pass

Rendered the burrow, roof attic and mushroom interior as actual 64×64 Frame buffers, and inspected all three at 1× and nearest-neighbor 8×. Assets: `assets/direction-*-native.png` and `assets/direction-*.png`. Reproduce with `python3 tools/workshop_directions.py`.

Chosen: **burrow workshop**, paired with a **moon greenhouse**. The burrow has the cleanest hierarchy: quiet dark teal architecture, small warm lamp/window accents, and a brass machine as the center of action. Attic ceiling/window/lamp compete for attention; mushroom roof is too large and red for the little actors below. The greenhouse leaves room around the recipient's pot and gives deliveries an obvious purpose.

Original cast: Nori, a mint courier with tall ears and a coral scarf; Bramble, a stocky maker with amber goggles and a teal apron; Rue, a lilac gardener under a mushroom bonnet. A small soot creature earns a place in the workshop through its biscuit mischief. Sprites are authored on the pixel grid with changing poses and feet, not rescaled illustrations.

First critique: held objects were floating too high above hands. Bring the grip and object together before animating the first story. Reserve contrast for faces, carried props and payoffs; use moderate-area illumination rather than full-frame flashes.

## Implementation and verification

Implementation and local verification are complete, with a physical single-device run on the existing selected Pixoo. Two-device synchronization is demonstrated in the local preview; no second physical address was selected.

## Stories implemented

- **An unlikely invention:** carrying the oversized cog, a preparation pause, crouch/toss, hammer strokes, a flower growing out of the machine, contained pollen sneeze, flying hat, catch and a glowing seed. Hat ownership and the lit workshop lamp persist.
- **A gift next door:** exactly one courier leaves the workshop, briefly travels between rooms, arrives with the same seed, plants it, celebrates the growing flower, and returns empty-handed. The recipient's flowers and hanging lanterns remain changed. On one display the equivalent gift grows in a workshop pot.
- **The biscuit bandit:** a little soot creature takes a biscuit, is caught, and splits it with Nori. After friendship, later visits bring biscuits instead of taking a biscuit already in the room; the creature wears a green scarf and helps sweep. Its little home persists.
- **Umbrella tea:** Nori catches the boiler's tea shower with an upside-down umbrella, discovers the mistake, turns it into a bowl and shares tea. Cups remain on the shelf; tea/friendship make subsequent inventions gentler, replacing the repeated sneeze/hat accident with fireflies.

Normal ambient intervals vary deterministically with the seed. Display compositions and local jobs differ: Bramble tends the machine while Rue waters the greenhouse and a snail moves on the sill. Flowers, cups and the event history are bounded. Showcase controls queue at story boundaries to preserve travelers and possessions.

Second visual pass: corrected hand/prop contact, separated whites and pupils, added blinking and cheerful/surprised faces, added a crouch and arc to the cog toss, made hammer strokes alternate, and clipped both silhouette and filling of split biscuit halves. Inspected the opening/handoff storyboards and the encoded tea recording's frame sequence. The browser automation connection failed during initialization; video containers and decoded frames were inspected with ffmpeg/ffprobe and the image viewer instead. The supplied HTML preview remains available for normal browser playback.

## Hardware evidence

The user confirmed that a Pixoo is available on this network and others could be selected at work. The existing selection, **192.168.4.111**, responded to a read-only configuration query. A process check found no existing Pixoo player before starting the physical run. No second physical display was selected or contacted.

First run: [hardware-single.json](assets/hardware-single.json), 75 seconds, **293 acknowledged frame uploads, zero transport failures**, about **3.92 fps**. Frame POST p50 **186.45 ms**, p95 **211.68 ms**, maximum **292.26 ms**. Largest body **16,505 bytes**; ten ID reset commands. These are measured physical HTTP acknowledgements, not visual/camera confirmation of each LED frame.

The first run restored brightness 100 but failed to preserve the original off state. Investigation initially suspected inverse power reporting; that hypothesis was falsified. [The controlled ordering probe](assets/hardware-power-order.json) shows:

1. `OnOffScreen 0` → `LightSwitch 0`.
2. `SetBrightness 100` → `LightSwitch 1` (brightness wakes the display).
3. `OnOffScreen 0` → `LightSwitch 0` again, restoring the original state.

Shutdown now restores brightness before screen power. The office-settings test pins this order. The physical probe polls final configuration and exits unsuccessfully if original brightness and screen power do not match.

Final run: [hardware-five-minutes.json](assets/hardware-five-minutes.json), **300 seconds, 1,163 acknowledged frames, one timeout followed by automatic recovery**, about **3.88 fps**. Successful frame POST p50 **186.48 ms**, p95 **214.72 ms**, maximum **294.53 ms**; the failed request timed out after **1,001.89 ms**. Largest body **16,505 bytes**, 37 ID resets. Stale pending frames were replaced 917 times as intended. All four interactions ran, including later friendly/gentle variations and repeated deliveries. Final configuration verifies **Brightness 100 and LightSwitch 0**, matching both original values. The run finished and left the display off.

At this rate, JSON frame traffic is about 64 KB/s per display before HTTP overhead. The worker has at most one in-flight frame and one pending frame; an offline device backs off to eight seconds. No growing animation queue or high-rate preloaded playback is involved.

## Final verification

- **38 regression tests pass**, including the original protocol and renderer goldens. The PTY cleanup check drains output and ignores only Darwin's transient PENDIN marker when comparing restored settings.
- [One-hour accelerated render soak](assets/soak-one-hour.json): 14,400 pairs of actual frames at simulated 4 fps; 89 completed stories, 25 deliveries, all four interaction types, 14,370 distinct frame pairs. Update plus two-world render p95 **0.704 ms** on this Mac, excluding terminal/network/PNG output. Event history stays at 128 entries, flowers at three per room and cups at three. This is simulated time, not an hour-long physical run.
- Single-world, two-world and tea recordings encode actual Program frames at 4 fps. Native and nearest-neighbor enlarged stills accompany them. Local CLI snapshot routing and real terminal input/cleanup are covered by regression tests.
- Physical appearance feedback was requested; no human response has arrived. Hardware evidence establishes acknowledged delivery, recovery and restored settings, not visual approval of the LEDs or synchronization across two real devices.
- Browser automation failed during initialization. Decoded recording frames and native PNGs were inspected directly; interactive browser playback was not automated.

The main remaining artistic limit is the intentionally small vocabulary of four stories. Persistent friendships, possessions, gifts, three flower kinds and varied quiet intervals change their context, but this is an authored miniature world, not an unlimited story generator. Later expansion should add meaningful reactions before adding more rooms or controls.
