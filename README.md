# SLAP Jetson Communication

Real-time control bridge between a TorchScript policy on a NVIDIA Jetson and a Teensy microcontroller that drives 12 motors.

```
Policy (TorchScript)
        │  joint positions + torques
        ▼
     Jetson  ──serial packets──►  Teensy  ──► motors
        ▲                           │
        └──── IMU / encoder feedback┘
```

## Requirements

**Hardware**

- NVIDIA Jetson (or any Linux machine with a CUDA/CPU PyTorch install)
- Teensy connected over USB serial (`ttyACM*` or a port whose description contains `Teensy`)
- 12-DOF robot with IMU + motor encoders on the Teensy side

**Software**

- Python 3.8+
- USB serial access (the user must be in the `dialout` group on Linux/Jetson)

```bash
pip install -r requirements.txt
```

Dependencies: `pyserial`, `torch`, `numpy`.

## Setup

1. Connect the Teensy over USB.
2. Confirm the port is visible:

   ```bash
   python -c "import serial.tools.list_ports as p; print([x.device for x in p.comports()])"
   ```

3. Point `MODEL_PATH` in `main.py` at a TorchScript (`.pt` / `.jit`) policy:

   ```python
   MODEL_PATH = '/path/to/policy.pt'
   ```

4. Grant serial access if needed:

   ```bash
   sudo usermod -aG dialout $USER
   ```

   Log out and back in after this change.

## Run

**Full control loop** (loads the policy, talks to the Teensy at 50 Hz):

```bash
python main.py
```

**Serial-only smoke test** (sends zero commands and prints IMU/encoder feedback):

```bash
python test.py
```

Stop either process with `Ctrl+C`. The control loop sends zero positions, zero torques, and `estop=True` before closing the port.

## Packet protocol

Little-endian binary structs over serial at **100000 baud**, 10 ms timeout.

| Direction | Format | Size | Payload |
|---|---|---|---|
| Jetson → Teensy | `<12f12f?` | 97 bytes | 12 joint positions, 12 torques, estop bool |
| Teensy → Jetson | `<21f` | 84 bytes | roll, pitch, yaw, gyro[3], accel[3], motor_positions[12] |

The Teensy firmware must pack/unpack these exact layouts. Incomplete reads (not 84 bytes) are treated as no feedback for that cycle.

## Control loop

`ModelController` in `ai_controller.py` runs at **50 Hz** by default:

1. Send the last commanded positions and torques (`estop=False`).
2. Build a 33-float observation: `[roll, pitch, yaw, gyro(3), accel(3), motor_positions(12), last_action(12)]`.
3. Run the TorchScript policy with `torch.no_grad()`.
4. Use the 12-float action as the next joint-position command. Torques are currently fixed at `2.0`.

On first cycles before a successful inference, positions default to zeros and torques to `0.5`.

## Project layout

| File | Role |
|---|---|
| `main.py` | Entry point: load policy, start the 50 Hz loop |
| `ai_controller.py` | Observation packing, inference, timing, estop on exit |
| `jetson_to_teensy.py` | Port discovery, pack/unpack, read/write |
| `test.py` | Loopback-style serial test with zero commands |
| `requirements.txt` | Python dependencies |

## Notes

- Port discovery looks for `"Teensy"` in the serial description or `"ttyACM"` in the device path. Other adapters will not be picked up without changing `find_teensy_port()`.
- The policy must accept a `[1, 33]` float32 tensor and return a `[1, 12]` action tensor.
- Baud rate (`100000`) and struct formats are hardcoded in `jetson_to_teensy.py`; they must match the Teensy firmware.
