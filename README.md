# meet Willow, your voice-activated virtual assistant.
Pooria Roy, Elliott Vince, Dolev Klein, Cait Roach

## intro
Navigating the internet can be difficult for disabled or elderly people, who often face obstacles to conducting daily tasks like online shopping, entering queries into search engines, watching videos, getting directions, or checking the weather. Because so much of our lives happens over the internet, this can lead to people feeling disconnected from their loved ones and the world around them.

In particular, with physical disabilities like cerebral palsy and arthritis experience pain from repetitive fine motor movements, like typing. Those who are visually impaired may struggle to read and write text. Seniors in particular face the most mobility and accessibility issues out of any age group. This means that our internet is racing towards a golden age of advanced technology while our most vulnerable groups are being left behind. 

Our project for QHacks 2026 is Willow: A simple, user-friendly program that allows the user to control their PC or laptop with conversational verbal commands, such as "show me a funny cat video", "look up a focaccia recipe", or "give me directions to the library". Using Willow, users can easily surf the Internet without touching their keyboard or relying on external assistance. We aim to provide our users with a highly accessible tool to improve their independence and agency.

## tech stack
- Eel Python application serving a vanilla HTML/JS/CSS application.

## ethics & privacy
Because our audience is made of vulnerable groups of people, privacy and security of our users' data is our highest priority. Willow is run locally on the users' device and can be disabled. No data leaves the computer and we do not collect any user information. In essence, Willow is a voice-activated virtual keyboard - not a companion or agent that would use data for model training.

Willow uses the device's microphone and our GUI provides a simple "mute" button that disables it. Upon startup, the mic is muted by default. This button can be quickly toggled with mouse clicks, the space bar, or the "enter" key. Otherwise, Willow waits to detect speech before processing user requests, similar to virtual assistants like Siri, Cortana, or Alexa.

## current limitations
