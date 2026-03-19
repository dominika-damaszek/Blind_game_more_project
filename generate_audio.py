import os
import subprocess

os.makedirs("audio", exist_ok=True)

phrases = {
    "Level 1": "Start_Level_one.wav",
    "Level 2": "Start_level_two.wav",
    "Level 3": "Start_level_three.wav",
    "Facing": "Facing.wav",
    "North": "North.wav",
    "South": "South.wav",
    "East": "East.wav",
    "West": "West.wav",
    "North East": "North-East.wav",
    "North West": "North-west.wav",
    "South East": "South-East.wav",
    "South West": "South-west.wav",
    "The goal is": "The_goal_is.wav",
    "CONGRATULATIONS! You have reached the goal!": "Congratulations.wav"
}

ps_script = 'Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Rate = 1; $synth.Volume = 90;'
for text, filename in phrases.items():
    filepath = os.path.abspath('audio/' + filename).replace('\\', '\\\\')
    ps_script += f"$synth.SetOutputToWaveFile('{filepath}'); $synth.Speak('{text}');"

subprocess.run(['powershell', '-Command', ps_script])
print("Generated all 14 audio files successfully in the audio/ folder!")
