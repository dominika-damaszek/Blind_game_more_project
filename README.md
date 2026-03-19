# Audio Maze & Hand Puzzle Game Hub

A fully accessible, web-based gaming hub featuring two unique interactive experiences designed with accessibility and novel input methods in mind.

## Features

### 🎧 Audio Maze
A blind-accessible maze game where players navigate entirely using acoustic cues.
- **Spatial Audio Navigation**: Listen for wind sounds in your left or right ear to find open corridors.
- **Goal Proximity Sonar**: A beeping sonar ping pulses faster as you get closer to the exit.
- **Obstacle Feedback**: Low thump sounds indicate when you have hit a wall.
- **Voice Control Integration**: Navigate using standard keyboard controls (WASD) or connect your microphone to control movement entirely with voice commands (powered by TensorFlow.js).
- **Comprehensive TTS**: The entire configuration menu is fully voiced, making it accessible to visually impaired users without a screen reader.

### 🖐️ Hand Puzzle
An optical gesture puzzle game that tracks your physical hands using computer vision.
- **Webcam Hand Tracking**: Uses MediaPipe to track hand gestures without any controllers.
- **Pinch-to-Grab Mechanics**: Physically pinch with your fingers in front of the camera to grab and move puzzle tiles.
- **Procedural Ambient Soundtrack**: Features a soothing, synthesized background track generated in real-time via the Web Audio API.

## Setup & Running Locally

Since the project uses webcam and microphone access (which require a secure context or localhost), you need to run a local web server.

1. Clone or download the repository.
2. Open a terminal in the project directory.
3. Start a local server (easiest way is using Python):
   ```bash
   python -m http.server 8080
   ```
4. Open your browser and navigate to `http://localhost:8080`.

## Built With
- **HTML/CSS/JS**: Vanilla web technologies.
- **Web Audio API**: For procedural synthesis and spatial panning.
- **TensorFlow.js**: For voice command recognition.
- **MediaPipe**: For hand landmark tracking.
