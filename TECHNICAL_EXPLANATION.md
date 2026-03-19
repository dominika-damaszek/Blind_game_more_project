# Technical Documentation: Audio Maze & Hand Puzzle Hub

## 1. Project Concept
The **Audio Maze & Hand Puzzle Hub** is an accessibility-first web application designed to create unique sensory experiences that cater to both visually impaired and sighted players. By challenging conventional game design, the project replaces traditional visual feedback and keyboard/mouse inputs with entirely novel paradigms:
- The **Audio Maze** strips away visual reliance, forcing the player to map out a procedurally generated labyrinth purely using acoustic feedback and voice controls. 
- The **Hand Puzzle** introduces an optical, gesture-driven approach, replacing controllers with computer vision, allowing the player to manipulate digital objects in real physical space.

The overarching goal of the project is to demonstrate advanced browser APIs, local Machine Learning integration, and procedural generation within a single static web application, hosted seamlessly and securely on **Netlify**.

---

## 2. Implemented Technologies

The project is built entirely on pure Web Technologies (HTML5, CSS3, ES6+ JavaScript) without heavy game engines like Unity or Unreal. Instead, it relies on powerful, modern browser APIs and lightweight neural networks.

### 2.1. Web Audio API (Procedural Synthesis)
Rather than loading large `.mp3` or `.wav` audio files, the vast majority of the game's soundscape is **procedurally generated in real-time** using mathematics.
- **Synthesizers**: In the Hand Puzzle, an ambient background track (an A-minor pentatonic sequence) is generated using `OscillatorNodes` mapped to specific frequencies. `BiquadFilterNodes` apply a low-pass filter to give the sound a muffled, atmospheric quality.
- **Volume Envelopes**: `GainNodes` are used to exponentially ramp audio volumes up and down smoothly, preventing audio clicking and allowing sounds to fade out naturally.
- **Spatial Audio**: In the Audio Maze, stereo panning is calculating by shooting virtual "rays" from the player's position. If the algorithm detects an open corridor to the left, it routes generated white noise heavily into the left audio channel, mimicking real-life acoustic wind.

### 2.2. TensorFlow.js & SpeechCommands AI
To allow for completely hands-free play, the Audio Maze integrates a custom Machine Learning model.
- **Local Execution**: The AI model is loaded and runs entirely within the user's browser via **TensorFlow.js**. No voice data is sent to an external server, preserving user privacy.
- **Audio Classification**: The `SpeechCommands` module listens to the microphone via Fourier Transforms (FFT) and compares the audio spectrogram against a trained dataset to instantly recognize navigational keywords (e.g., "Left", "Right", "Forward").

### 2.3. MediaPipe Hands (Computer Vision)
For the Hand Puzzle, the physical world is connected to the digital canvas using **Google MediaPipe**.
- **Hand Landmarks**: High-fidelity algorithmic tracking identifies 21 3D landmarks across the user's hands via the webcam.
- **Euclidean Distance Math**: By continuously calculating the Euclidean distance between the tip of the index finger (Landmark 8) and the tip of the thumb (Landmark 4), the JavaScript code determines if the user is performing a "Pinch" gesture. This is used to grab and drag puzzle pieces across the HTML5 Canvas.

### 2.4. Web Speech API (Text-to-Speech)
The project builds its own robust screen-reader capabilities using the native `window.speechSynthesis` API.
- Because native TTS can suffer from memory and garbage-collection bugs on long lists of UI elements, the project wraps the TTS engine in a custom architectural layer. 
- Short, debounced JavaScript timeouts intercept the text extraction, sanitize it of non-readable elements, and sequentially buffer the audio so that hovering rapidly across menus feels instantaneous and responsive without crashing the audio thread.

### 2.5. HTML5 Canvas & Procedural Generation
- **Maze Generation**: The layout of the Audio Maze is generated on-the-fly using a **Randomized Depth-First Search (DFS)** algorithm. Starting from an origin point, the algorithm "carves" paths through a solid grid, using a backtracking stack to ensure a valid, solvable maze is created every time.
- **Canvas Rendering**: Both games use the `<canvas>` API to rapidly render visual representations at 60 FPS using `requestAnimationFrame`, handling image cropping and coordinate interpolation for smooth visual lerping.

---

## 3. Architecture & Deployment
- **Client-Side Execution**: All intensive processing (game loops, neural network inferencing, audio synthesis) is offloaded to the client CPU/GPU architecture.
- **Netlify Hosting**: Because the application utilizes APIs that require a **Secure Context** (Webcam and Microphone API), it is deployed to production via **Netlify**, ensuring everything is served over HTTPS with global edge-network fast delivery.
