## Live Demo

Access the deployed web app here:

https://vitcheck-a-smart-fitness-webpage.onrender.com/

# Smart Fitness & Nutrition Tracker

A Python Flask web application that helps users track workouts, meals, body weight, and fitness progress. The system uses AI-assisted recommendations and linear regression-style prediction to help users understand their weekly fitness progress and make better health decisions.

## Project Type

Python Web Application using Flask

## Purpose

The Smart Fitness & Nutrition Tracker is designed to act as a personalized fitness assistant. Users can record their daily workouts, meals, calorie intake, and weight changes. Based on the collected data, the app predicts progress and provides suggestions such as reducing calorie intake, increasing cardio time, or improving workout consistency.

## Core Idea

Users input daily fitness and nutrition data, including:

- Exercise type
- Workout duration
- Workout intensity
- Calories consumed from meals
- Body weight updates

The system then helps predict:

- Possible weight gain or weight loss
- Fitness progress toward the user's goal
- Weekly weight trend
- Possible plateau or stagnant progress

Based on the results, the app can recommend adjustments such as:

- Eat fewer calories
- Add more cardio minutes
- Increase workout duration
- Improve consistency with logging meals and workouts

## Features

### 1. User Profile

Users can create a personal profile that stores important fitness information such as:

- Name
- Age
- Gender
- Height
- Starting weight
- Target weight
- Fitness goal: lose, gain, or maintain weight

### 2. Workout Tracker

Users can log workout activities with:

- Workout type
- Duration
- Intensity
- Date and time

This helps users monitor their physical activity and stay consistent with their fitness routine.

### 3. Meal Tracker

Users can record meals and calorie intake. This feature helps users understand how their eating habits affect their progress.

### 4. Progress Prediction

The app uses linear regression-style trend analysis to estimate future weight changes based on the user's logged weight data. This helps users see whether they are moving closer to their goal.

### 5. Goal Tracker

The system tracks progress toward the user's target weight and fitness goal. It can display progress visually through graphs and progress indicators.

### 6. Smart Plateau Detection

The unique feature of this project is Smart Plateau Detection.

The system analyzes the user's weight data over time. If the predicted weight change becomes very small or nearly zero, the app identifies a possible fitness plateau. A plateau means the user's progress has slowed down or stopped.

When a plateau is detected, the app can suggest adjustments such as:

- Reducing calorie intake
- Adding more cardio
- Increasing workout duration
- Increasing workout intensity

### 7. AI-Powered Fitness Assistance

The app includes AI-assisted features that can help generate fitness insights, recommendations, and calorie-related guidance. These features help make the app feel more like a personal fitness assistant.

## Technologies Used

- Python
- Flask
- Firebase / Firestore
- Firebase Storage
- Flask-Login
- Google Gemini API
- NumPy
- HTML
- CSS
- JavaScript

## Installation and Setup

Follow these steps to install and run the Smart Fitness & Nutrition Tracker on your local computer.

### 1. Clone the Repository

Open your terminal or VS Code terminal, then run:

```bash
git clone https://github.com/mitsa007/proglang.git
cd proglang
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

### 3. Activate the Virtual Environment

For Windows PowerShell:

```bash
.venv\Scripts\activate
```

For Command Prompt:

```bash
.venv\Scripts\activate.bat
```

For macOS/Linux:

```bash
source .venv/bin/activate
```

After activation, your terminal should show something like:

```bash
(.venv)
```

### 4. Install Dependencies

Install all required Python packages using:

```bash
pip install -r requirements.txt
```

If some packages are missing, install them manually:

```bash
pip install Flask flask-login firebase-admin google-genai python-dotenv numpy Werkzeug
```

### 5. Set Up Environment Variables

Create a file named `.env` in the project root directory.

Inside the `.env` file, add:

```env
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=your_secret_key_here
```

Replace `your_gemini_api_key_here` with your actual Google Gemini API key.

The `GEMINI_API_KEY` is used for AI-powered recommendations and calorie estimation.

The `SECRET_KEY` is used by Flask for session security.

### 6. Set Up Firebase

This project uses Firebase / Firestore as the database.

To set up Firebase:

1. Go to the [Firebase Console](https://console.firebase.google.com/).
2. Select your Firebase project or create a new one.
3. Click the **Gear Icon** beside **Project Overview**.
4. Select **Project settings**.
5. Go to the **Service accounts** tab.
6. Click **Generate new private key**.
7. Download the JSON file.
8. Rename the downloaded file to:

```text
serviceAccountKey.json
```

9. Place `serviceAccountKey.json` in the project root directory, beside `app.py`.

Example project structure:

```text
proglang/
│
├── app.py
├── README.md
├── requirements.txt
├── .env
├── serviceAccountKey.json
├── static/
├── templates/
└── src/
```

### 7. Make Sure Secret Files Are Ignored

Do not upload API keys, database files, or Firebase credentials to GitHub.

Make sure your `.gitignore` file includes:

```gitignore
.env
serviceAccountKey.json
database.db
.venv/
__pycache__/
*.pyc
```

To check if your secret files are not being tracked by Git, run:

```bash
git status
```

The following files should not appear in the list of files to commit:

```text
.env
serviceAccountKey.json
database.db
```

### 8. Run the Application

Run the Flask application using:

```bash
python -m flask --app app run
```

### 9. Access the App

After running the app, open your browser and go to:

```text
http://127.0.0.1:5000
```

or:

```text
http://localhost:5000
```

### 10. Common Issues and Fixes

#### Virtual environment cannot be activated on Windows

If PowerShell blocks the activation command, run:

```bash
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate the virtual environment again:

```bash
.venv\Scripts\activate
```

#### Missing module error

If you see an error like:

```text
ModuleNotFoundError: No module named 'package_name'
```

Install the missing package:

```bash
pip install package_name
```

Then update `requirements.txt`:

```bash
pip freeze > requirements.txt
```

#### Firebase key not found

If the app says `serviceAccountKey.json` is missing, make sure the file:

- Is inside the project root folder
- Is named exactly `serviceAccountKey.json`
- Is not named `serviceAccountKey.json.json`

#### Flask app does not run

Try running:

```bash
python -m flask --app app run --debug
```

### 11. Installation Command Summary

```bash
git clone https://github.com/mitsa007/proglang.git
cd proglang
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m flask --app app run
```

Then open:

```text
http://127.0.0.1:5000
```

## Usage

### Onboarding

First-time users need to create a profile by entering their personal fitness details, such as:

- Name
- Age
- Gender
- Height
- Starting weight
- Target weight
- Fitness goal

### Logging Workouts and Meals

Users can:

- Log daily workouts with duration and intensity
- Log meals with estimated calories
- Update body weight regularly
- Track fitness habits over time

### Monitoring Progress

Users can:

- View progress through charts and graphs
- Monitor weight trends
- Check goal achievement
- Detect possible fitness plateaus

### AI Assistance

The app provides AI-generated recommendations and fitness insights to help users improve their fitness journey.

## Key Features

- User Profiles
- Workout Tracking
- Meal Tracking
- Progress Prediction
- Goal Setting
- Smart Plateau Detection
- AI Assistance
- Firebase Integration
- Progress Visualization
- Web-Based Interface

## How Linear Regression Is Used

The app analyzes previous weight logs and uses the trend of the data to estimate future progress. If the weight trend is moving in the expected direction, the user is likely progressing toward the goal. If the trend becomes flat or nearly unchanged, the system may detect a possible fitness plateau.

Example:

- For a weight loss goal, weight should gradually decrease.
- For a weight gain goal, weight should gradually increase.
- For a maintenance goal, weight should remain stable.

## Example Recommendations

The app may suggest:

```text
Eat 200 kcal less per day.
Add 20 minutes of cardio.
Increase workout intensity.
Stay consistent with meal tracking.
Log your weight regularly for better predictions.
```

## Security Notes

This project uses API keys and Firebase credentials. These files must not be uploaded to GitHub:

```text
.env
serviceAccountKey.json
database.db
```

The Firebase service account key should only be stored locally or configured securely in the deployment platform.

## Recommended Requirements

Your `requirements.txt` should include the packages needed to run the project:

```text
Flask
flask-login
firebase-admin
google-genai
python-dotenv
numpy
Werkzeug
gunicorn
```

## Future Enhancements

- Add image-based meal recognition
- Implement custom workout plans
- Add weekly and monthly progress reports
- Integrate with fitness wearables
- Add gamification elements
- Provide more advanced AI-powered health insights
- Improve mobile responsiveness
- Add exportable fitness reports

## Author

Created by Mitsa  
GitHub: [mitsa007][def]

[def]: https://github.com/mitsa007