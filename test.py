from jetson_to_teensy import JetsonTeensyBridge

def main():
    bridge = JetsonTeensyBridge()
    try:
        while True:
            positions = [0.0] * 12
            torques = [0.0] * 12
            estop = False

            imu_motor_feedback = bridge.communicate(positions, torques, estop)
            if imu_motor_feedback:
                print(f"Feedback: {imu_motor_feedback}")
            else:
                print("No feedback received.")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        bridge.close()

if __name__ == "__main__":
    main()