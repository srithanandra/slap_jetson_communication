import torch
import numpy as np
import time
from jetson_to_teensy import JetsonTeensyBridge

MODEL_PATH = ''

class ModelController:
    def __init__(self, model_path):
        try:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.policy = torch.jit.load(model_path, map_location=self.device)
            self.policy.eval()
        except Exception as e:
            raise SystemExit(f'Failed to load AI model: {e}')

        self.bridge = JetsonTeensyBridge()
        self.last_action = np.zeros(12, dtype=np.float32)
        self.default_positions = np.zeros(12, dtype=np.float32)

    def extract_observation_vector(self, feedback):
        try:
            obs = []
            obs.extend([feedback['roll'], feedback['pitch'], feedback['yaw']])
            obs.extend(feedback['gyro'])
            obs.extend(feedback['accel'])
            obs.extend(feedback['motor_positions'])
            obs.extend(self.last_action.tolist())
            
            obs_tensor = torch.tensor([obs], dtype=torch.float32, device=self.device)
            return obs_tensor
        except KeyError as e:
            print(f'Observation extraction error: Missing key {e}')
            return None

    def run_loop(self, frequency=50):
        dt = 1.0 / frequency
        positions = self.default_positions.tolist()
        torques = [0.5] * 12

        try:
            while True:
                start_time = time.time()
                feedback = self.bridge.communicate(positions, torques, estop=False)

                if feedback:
                    obs_tensor = self.extract_observation_vector(feedback)
                    
                    if obs_tensor is not None:
                        with torch.no_grad():
                            action_tensor = self.policy(obs_tensor)
                        
                        actions = action_tensor.cpu().numpy()[0]
                        self.last_action = actions
                        
                        positions = actions.tolist()
                        torques = [2.0] * 12

                elapsed = time.time() - start_time
                if elapsed < dt:
                    time.sleep(dt - elapsed)
                    
        except KeyboardInterrupt:
            print('Shutting down')
            self.bridge.communicate([0.0]*12, [0.0]*12, estop=True)
            self.bridge.close()
        except Exception as e:
            print(f'Runtime control loop error: {e}')
            self.bridge.communicate([0.0]*12, [0.0]*12, estop=True)
            self.bridge.close()

if __name__ == '__main__':
    controller = ModelController(MODEL_PATH)
    controller.run_loop(frequency=50)