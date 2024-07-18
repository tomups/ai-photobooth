# AI Tinkerers Photobooth

An interactive photobooth application using Stable Diffusion 1.5 for AI-powered image generation with face preservation.

Fully local (hope you have a decent GPU!).

## Features

- Real-time webcam feed
- Countdown timer for photo capture
- AI-powered image generation using Stable Diffusion 1.5 with various artistic styles
- Image composition preservation via controlnets
- Mask-based face preservation to maintain recognizable facial features
- Printing capability for generated images (tested on Canon Selphy CP1300)
- Fullscreen toggle (alt+enter)
- On-screen and on-print branding
- Sound effects

## Requirements

- PyGame Community Edition
- OpenCV (cv2)
- imaginAIry https://github.com/brycedrennan/imaginAIry
- PIL

## IMPORTANT

This has been tailored for my particular laptop, running on Windows. It might need adjustments for your own environment.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/ai-tinkerers-photobooth.git
   cd ai-tinkerers-photobooth
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the main application:

```python main.py```

Press space to do a photo capture. After 3 photos, they will be printed.

NOTE: The first generation takes longer as it has to load the model.