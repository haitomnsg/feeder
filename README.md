# Megawatt (MW) Prediction Project

This project implements a comprehensive analysis and prediction system for Megawatt (MW) consumption using various machine learning and deep learning models.

## Overview

The project uses weather data and time-based features to predict MW (Megawatt) consumption. It implements and compares multiple models to find the best performing approach.

## Models Implemented

### Machine Learning Models
- **Support Vector Regression (SVR)**: Kernel-based regression model
- **Random Forest**: Ensemble learning method using decision trees
- **XGBoost**: Gradient boosting framework

### Deep Learning Models
- **LSTM (Long Short-Term Memory)**: Recurrent neural network for sequence prediction
- **GRU (Gated Recurrent Unit)**: Simplified variant of LSTM

## Evaluation Metrics

All models are evaluated using:
- **RMSE** (Root Mean Square Error)
- **MAE** (Mean Absolute Error)
- **MSE** (Mean Square Error)
- **R²** (R-squared / Coefficient of Determination)
- **MAPE** (Mean Absolute Percentage Error)

## Dataset

- **Source**: `combinedMVWeatherData/combinedMVWeather.xlsx`
- **Samples**: 24,528 hourly readings
- **Features**:
  - Air Temperature (°C)
  - Global Solar Radiation (W/m²)
  - Relative Humidity (%)
  - Time-based features (hour, day, month, etc.)
- **Target**: MW (Megawatt consumption)

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

2. Launch Jupyter Notebook:
```bash
jupyter notebook
```

3. Open `MV_Prediction_Analysis.ipynb`

## Notebook Structure

1. **Import Libraries**: Load all necessary packages
2. **Load and Explore Dataset**: Initial data exploration
3. **Data Preprocessing**: Handle missing values, feature engineering
4. **Exploratory Data Analysis (EDA)**: Comprehensive visualizations
5. **Prepare Data for Modeling**: Train-test split and scaling
6. **Machine Learning Models**: Train SVR, Random Forest, XGBoost
7. **Deep Learning Models**: Train LSTM and GRU models
8. **Model Evaluation**: Compare all models using multiple metrics
9. **Prediction Curves**: Visualize model predictions
10. **Interactive Prediction System**: Interface for making predictions
11. **Summary and Conclusions**: Final results and insights

## Features

### Data Preprocessing
- Missing value imputation using interpolation
- Time-based feature extraction (hour, day, month, etc.)
- Cyclical encoding for temporal features
- Feature scaling (StandardScaler and MinMaxScaler)

### Visualizations
- MW consumption distribution and trends
- Time series plots
- Hourly and monthly consumption patterns
- Correlation heatmaps
- Feature importance analysis
- Model performance comparisons
- Prediction vs. actual curves for all models
- Scatter plots for prediction accuracy

### Interactive Prediction
A function is provided to make predictions based on user inputs:
```python
predict_mw(air_temp=20.0, solar_radiation=400, humidity=65, 
           hour=12, day=15, month=6, day_of_week=2, 
           day_of_year=166, model='XGBoost')
```

## Results

The notebook provides:
- Comprehensive model comparison table
- Visual comparisons of all metrics
- Prediction curves showing actual vs predicted values
- Feature importance analysis
- Best performing model identification

## Usage

1. **Run the notebook cells sequentially** to:
   - Load and preprocess data
   - Train all models
   - Generate visualizations
   - Evaluate model performance

2. **Use the prediction function** to forecast MW consumption:
   - Input weather conditions and time information
   - Select preferred model
   - Get instant MW prediction

3. **Compare models** using the comprehensive evaluation metrics and visualizations provided

## Project Structure

```
feeder/
├── MV_Prediction_Analysis.ipynb  # Main analysis notebook
├── requirements.txt               # Python dependencies
├── README.md                      # This file
├── combinedMVWeatherData/
│   └── combinedMVWeather.xlsx    # Dataset
├── dataset/                       # Raw data folders
├── extractedDataset/             # Processed data
└── structuredDataset/            # Structured data
```

## Notes

- The notebook is self-contained and can be run from start to finish
- Deep learning models may take longer to train (10-20 minutes)
- All visualizations are generated automatically
- Models are evaluated on a held-out test set (20% of data)

## Future Enhancements

Potential improvements:
- Hyperparameter tuning using GridSearch/RandomSearch
- Additional feature engineering
- Ensemble methods combining multiple models
- Real-time prediction API
- Model deployment as web service

## Author

Project developed for MW consumption prediction using machine learning and deep learning techniques.

## License

This project is provided as-is for educational and research purposes.
