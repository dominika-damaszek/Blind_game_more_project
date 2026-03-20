# Audio Maze & Hand Puzzle Gaming Hub

Welcome to the **Audio Maze & Hand Puzzle Hub**, an accessibility-first web application featuring a collection of unique, browser-based games. This project challenges conventional game design by replacing traditional visual feedback and keyboard/mouse inputs with entirely novel paradigms: acoustic navigation and physical hand gestures.

The overarching goal of the project is to demonstrate the power of modern browser APIs, local Machine Learning integration, computer vision, and procedural generation within a single static web application—entirely built without heavy game engines like Unity or Unreal.

---

## 🎮 The Games

### 1. 🎧 Audio Maze (The Blind Game)
The Audio Maze is a labyrinth game explicitly designed for players with visual impairments. It completely relies on sound over sight, forcing the player to map out and navigate a procedurally generated maze using only acoustic feedback and vocal commands.

**Game Mechanics & Features:**
- **Spatial Audio Navigation**: The game uses intelligent stereo panning. By shooting virtual "rays" from the player's position, the game detects open corridors. If an open path is to your left, you will hear a generated wind sound heavily routed into your left audio channel.
- **Goal Proximity Sonar**: As you move closer to the maze's exit, a rhythmic radar/sonar ping pulses faster, acting as an acoustic compass.
- **Obstacle Feedback**: Attempting to move into a wall or dead end will trigger a low, bass-heavy thump sound.
- **Voice Control Integration (AI)**: Players can navigate completely hands-free. Thanks to an integrated Machine Learning model running locally in the browser, the game recognizes verbal commands (e.g., "Left", "Right", "Forward"). Conventional keyboard controls (WASD) are also supported.
- **Procedural Maze Generation**: No two games are the same. The layout of the maze is generated on-the-fly using a Randomized Depth-First Search (DFS) algorithm, ensuring a valid, solvable labyrinth every single playthrough.
- **Comprehensive Text-To-Speech (TTS)**: The entire configuration menu and UI are fully voiced using a custom architectural wrapper around the browser's native speech synthesis, making it accessible even without an external screen reader.

### 2. 🖐️ Hand Puzzle
The Hand Puzzle is an optical, gesture-driven drag-and-drop game. It replaces physical controllers and mice with cutting-edge computer vision, allowing you to manipulate digital puzzle pieces in real physical space using your webcam.

**Game Mechanics & Features:**
- **Webcam Hand Tracking**: The game continuously maps the physical position of your hands and fingers in 3D space.
- **Pinch-to-Grab Mechanics**: By calculating the Euclidean distance between the tip of your index finger and thumb, the game determines when you are performing a "Pinch" gesture. This allows you to naturally grab, drag, and drop puzzle tiles across the screen.
- **Procedural Ambient Soundtrack**: While playing, you will hear a soothing, ambient background track (an A-minor pentatonic sequence). This is not an audio file; it is synthesized entirely in real-time using mathematical oscillators and low-pass filters mapped to specific frequencies.

---

## 🛠️ Behind the Scenes: Technologies Used

This project is built using pure **HTML5, CSS3, and modern JavaScript (ES6+)**. All intensive heavy-lifting is offloaded to the client CPU/GPU.

* **Web Audio API**: Powers the procedural sound synthesis. `OscillatorNodes` generate raw soundwaves, `BiquadFilterNodes` muffle atmospheres, `GainNodes` provide smooth volume envelopes to prevent audio clipping, and spatial audio panning mimics real-life acoustics.
* **TensorFlow.js & SpeechCommands AI**: A custom trained neural network model is loaded locally in the browser. It listens to the microphone via Fast Fourier Transforms (FFT) and compares audio spectrograms to recognize specific spoken navigation keywords instantly.
* **Google MediaPipe Hands**: Performs high-fidelity algorithmic tracking to identify 21 3D landmarks across the user's hands via the webcam stream.
* **Web Speech API**: Native `window.speechSynthesis` is utilized to create an instant, responsive, and robust self-contained screen reader for the game's menus.
* **HTML5 Canvas**: Handles the rapid rendering of visual representations (like the maze layout and puzzle tiles) at 60 FPS using `requestAnimationFrame`.

---

## 🔒 Privacy & Architecture
- **100% Client-Side Execution**: All artificial intelligence inferencing, audio recording, and webcam tracking happen entirely locally on your device. **No video or voice data is ever sent to an external server**, strict privacy is preserved for the users. 

---

## 🚀 Setup & Running Locally

Because the application requires access to the webcam and microphone (which browsers only allow in secure contexts or `localhost`), you must run the project via a local web server, rather than just opening the HTML files directly.

1. **Clone or Download** this repository to your machine.
2. **Open a Terminal / Command Prompt** inside the project folder.
3. **Start a local HTTP server.** If you have Python installed, you can easily do this by running:
   ```bash
   python -m http.server 8080
   ```
4. **Play:** Open your web browser and navigate to `http://localhost:8080` (or whichever port the server assigned).
