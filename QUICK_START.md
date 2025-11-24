# Quick Start Guide

## MV Prediction Project - Getting Started

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)

### Installation Steps

1. **Clone the repository** (if not already done):
   ```bash
   git clone https://github.com/haitomnsg/feeder.git
   cd feeder
   ```

2. **Install required packages**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch Jupyter Notebook**:
   ```bash
   jupyter notebook
   ```

4. **Open the notebook**:
   - In your browser, navigate to `MV_Prediction_Analysis.ipynb`
   - Click to open it

### Running the Notebook

#### Option 1: Run All Cells (Recommended for first time)
1. Click on **Cell** menu → **Run All**
2. Wait for all cells to execute (this may take 15-30 minutes for deep learning models)
3. Scroll through to see all visualizations and results

#### Option 2: Run Step by Step
1. Start from the first cell
2. Press **Shift + Enter** to run each cell and move to the next
3. Review outputs and visualizations as you go

### What to Expect

The notebook will:
1. **Load the dataset** (24,528 samples)
2. **Preprocess data** and handle missing values
3. **Generate visualizations**:
   - MW distribution
   - Time series plots
   - Hourly and monthly patterns
   - Correlation heatmap
   - Feature relationships
4. **Train 5 models**:
   - SVR (~1-2 minutes)
   - Random Forest (~2-3 minutes)
   - XGBoost (~2-3 minutes)
   - LSTM (~10-15 minutes)
   - GRU (~10-15 minutes)
5. **Evaluate and compare** all models
6. **Generate prediction curves** for visualization
7. **Provide interactive prediction** function

### Expected Outputs

Each section produces:
- **EDA Section**: 8+ visualization plots
- **Training Section**: Progress bars and training logs
- **Evaluation Section**: Performance comparison table and charts
- **Predictions Section**: Prediction curves and scatter plots
- **Summary**: Complete results overview

### Using the Prediction Function

After running all cells, you can make custom predictions:

```python
# Example usage
prediction = predict_mw(
    air_temp=20.0,           # Air Temperature in °C
    solar_radiation=400,      # Solar Radiation in W/m²
    humidity=65,              # Relative Humidity in %
    hour=12,                  # Hour of day (0-23)
    day=15,                   # Day of month (1-31)
    month=6,                  # Month (1-12)
    day_of_week=2,            # Day of week (0=Mon, 6=Sun)
    day_of_year=166,          # Day of year (1-365)
    model='XGBoost'           # Model choice
)

print(f'Predicted MW: {prediction:.2f}')
```

### Tips for Success

1. **Be patient**: Deep learning models take time to train
2. **Save your work**: Click **File** → **Save and Checkpoint** regularly
3. **Restart kernel if needed**: **Kernel** → **Restart & Clear Output**
4. **Check outputs**: Review each visualization to understand the data
5. **Experiment**: Try different parameters in the prediction function

### Troubleshooting

#### Problem: "Module not found" error
**Solution**: Make sure you installed all requirements:
```bash
pip install -r requirements.txt
```

#### Problem: Notebook won't open
**Solution**: Verify Jupyter is installed:
```bash
pip install jupyter
```

#### Problem: Training takes too long
**Solution**: This is normal. Deep learning models can take 10-20 minutes. Consider:
- Running on a machine with GPU support
- Reducing `epochs` parameter (e.g., from 100 to 50)
- Using only ML models (SVR, Random Forest, XGBoost) for faster results

#### Problem: Out of memory
**Solution**: 
- Close other applications
- Restart the notebook kernel
- Reduce `batch_size` for deep learning models

### Key Results to Look For

1. **Model Comparison Table**: Shows which model performs best
2. **RMSE, MAE, R²** values: Lower RMSE/MAE and higher R² are better
3. **Prediction Curves**: How well predictions match actual values
4. **Feature Importance**: Which features matter most

### Next Steps

After running the notebook:
1. Review the model comparison to identify the best model
2. Experiment with the prediction function
3. Consider hyperparameter tuning for better results
4. Deploy the best model for real-world predictions

### Getting Help

If you encounter issues:
1. Check the notebook outputs for error messages
2. Verify all imports work (run the first cell)
3. Ensure the dataset file exists: `combinedMVWeatherData/combinedMVWeather.xlsx`
4. Check Python version: `python --version` (should be 3.9+)

### Project Structure

```
feeder/
├── MV_Prediction_Analysis.ipynb  ← START HERE
├── requirements.txt               ← Install these first
├── README.md                      ← Full documentation
├── QUICK_START.md                 ← This file
└── combinedMVWeatherData/
    └── combinedMVWeather.xlsx    ← Dataset
```

---

**Ready to start?** Open `MV_Prediction_Analysis.ipynb` and run all cells!

Good luck with your MW prediction project! 🚀
