"""
Microplastics Synthetic Data Generator

This module generates synthetic microplastics data from 1993-2025 using TimeGAN
and environmental conditioning to extend the existing NOAA dataset.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from datetime import datetime, timedelta
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# ML imports for synthetic generation
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

class MicroplasticsDataProcessor:
    """
    Processes NOAA microplastics data for synthetic generation
    """
    
    def __init__(self, data_path: str = None, output_dir: str = None):
        """
        Initialize the processor
        
        Args:
            data_path: Path to the NOAA microplastics CSV file
            output_dir: Output directory for processed data
        """
        self.data_path = data_path or "/Users/marco/Downloads/Marine_Microplastics_WGS84_8553846406879449657.csv"
        self.output_dir = output_dir or "/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords/microplastics"
        self.raw_data = None
        self.processed_data = None
        self.scalers = {}
        self.encoders = {}
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Create output directory
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def load_data(self) -> pd.DataFrame:
        """
        Load and perform initial cleaning of NOAA microplastics data
        
        Returns:
            Cleaned DataFrame
        """
        self.logger.info(f"Loading data from {self.data_path}")
        
        try:
            # Load CSV with proper encoding
            self.raw_data = pd.read_csv(self.data_path, encoding='utf-8-sig')
            
            # Clean column names (remove BOM and standardize)
            self.raw_data.columns = [col.strip().replace('\ufeff', '') for col in self.raw_data.columns]
            
            # Basic info about the dataset
            self.logger.info(f"Loaded {len(self.raw_data)} records")
            self.logger.info(f"Columns: {list(self.raw_data.columns)}")
            
            return self.raw_data
            
        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            raise
    
    def analyze_temporal_coverage(self) -> Dict:
        """
        Analyze temporal coverage of the dataset
        
        Returns:
            Dictionary with temporal analysis results
        """
        if self.raw_data is None:
            self.load_data()
        
        # Extract date information
        date_col = 'Date (MM-DD-YYYY)'
        if date_col not in self.raw_data.columns:
            # Find the date column
            date_cols = [col for col in self.raw_data.columns if 'date' in col.lower()]
            if date_cols:
                date_col = date_cols[0]
            else:
                raise ValueError("No date column found")
        
        # Parse dates
        self.raw_data['parsed_date'] = pd.to_datetime(self.raw_data[date_col], errors='coerce')
        self.raw_data['year'] = self.raw_data['parsed_date'].dt.year
        self.raw_data['month'] = self.raw_data['parsed_date'].dt.month
        
        # Temporal analysis
        year_counts = self.raw_data['year'].value_counts().sort_index()
        date_range = {
            'min_year': self.raw_data['year'].min(),
            'max_year': self.raw_data['year'].max(),
            'total_records': len(self.raw_data),
            'year_distribution': year_counts.to_dict(),
            'records_per_year': year_counts.describe().to_dict()
        }
        
        self.logger.info(f"Temporal coverage: {date_range['min_year']}-{date_range['max_year']}")
        self.logger.info(f"Peak year: {year_counts.idxmax()} with {year_counts.max()} records")
        
        return date_range
    
    def analyze_spatial_coverage(self) -> Dict:
        """
        Analyze spatial coverage and distribution
        
        Returns:
            Dictionary with spatial analysis results
        """
        if self.raw_data is None:
            self.load_data()
        
        # Spatial analysis
        lat_col = 'Latitude (degree)'
        lon_col = 'Longitude(degree)'
        
        spatial_stats = {
            'latitude_range': [self.raw_data[lat_col].min(), self.raw_data[lat_col].max()],
            'longitude_range': [self.raw_data[lon_col].min(), self.raw_data[lon_col].max()],
            'ocean_distribution': self.raw_data['Ocean'].value_counts().to_dict() if 'Ocean' in self.raw_data.columns else {},
            'region_distribution': self.raw_data['Region'].value_counts().to_dict() if 'Region' in self.raw_data.columns else {},
            'total_locations': len(self.raw_data.groupby([lat_col, lon_col]))
        }
        
        self.logger.info(f"Spatial coverage: Lat {spatial_stats['latitude_range']}, Lon {spatial_stats['longitude_range']}")
        self.logger.info(f"Unique locations: {spatial_stats['total_locations']}")
        
        return spatial_stats
    
    def analyze_concentration_patterns(self) -> Dict:
        """
        Analyze microplastics concentration patterns
        
        Returns:
            Dictionary with concentration analysis results
        """
        if self.raw_data is None:
            self.load_data()
        
        # Find concentration column
        concentration_col = 'Microplastics measurement'
        if concentration_col not in self.raw_data.columns:
            # Look for alternatives
            conc_cols = [col for col in self.raw_data.columns if 'measurement' in col.lower() or 'concentration' in col.lower()]
            if conc_cols:
                concentration_col = conc_cols[0]
            else:
                raise ValueError("No concentration column found")
        
        # Clean concentration data
        concentrations = pd.to_numeric(self.raw_data[concentration_col], errors='coerce')
        concentrations = concentrations.dropna()
        
        concentration_stats = {
            'count': len(concentrations),
            'mean': concentrations.mean(),
            'median': concentrations.median(),
            'std': concentrations.std(),
            'min': concentrations.min(),
            'max': concentrations.max(),
            'quantiles': concentrations.quantile([0.25, 0.5, 0.75, 0.9, 0.95, 0.99]).to_dict(),
            'zero_concentration_pct': (concentrations == 0).mean() * 100
        }
        
        # Concentration class distribution
        if 'Concentration class text' in self.raw_data.columns:
            concentration_stats['class_distribution'] = self.raw_data['Concentration class text'].value_counts().to_dict()
        
        self.logger.info(f"Concentration stats: Mean={concentration_stats['mean']:.6f}, Median={concentration_stats['median']:.6f}")
        self.logger.info(f"Zero concentrations: {concentration_stats['zero_concentration_pct']:.1f}%")
        
        return concentration_stats
    
    def prepare_time_series_features(self, target_years: List[int] = None) -> pd.DataFrame:
        """
        Prepare features for time series modeling
        
        Args:
            target_years: Years to include (default: 1993-2023)
            
        Returns:
            Processed DataFrame ready for modeling
        """
        if self.raw_data is None:
            self.load_data()
        
        if target_years is None:
            target_years = list(range(1993, 2024))  # 1993-2023
        
        # Filter data for target years
        filtered_data = self.raw_data[self.raw_data['year'].isin(target_years)].copy()
        
        # Core features for modeling
        feature_columns = [
            'Latitude (degree)', 'Longitude(degree)', 'year', 'month',
            'Microplastics measurement', 'Ocean Bottom Depth (m)'
        ]
        
        # Check which columns exist
        available_columns = [col for col in feature_columns if col in filtered_data.columns]
        
        # Create processed dataset
        processed = filtered_data[available_columns].copy()
        
        # Handle missing values
        processed = processed.dropna(subset=['Microplastics measurement'])
        
        # Add derived features
        processed['season'] = processed['month'].map({
            12: 'winter', 1: 'winter', 2: 'winter',
            3: 'spring', 4: 'spring', 5: 'spring',
            6: 'summer', 7: 'summer', 8: 'summer',
            9: 'fall', 10: 'fall', 11: 'fall'
        })
        
        # Coordinate transformations for modeling
        processed['lat_rad'] = np.radians(processed['Latitude (degree)'])
        processed['lon_rad'] = np.radians(processed['Longitude(degree)'])
        processed['lat_sin'] = np.sin(processed['lat_rad'])
        processed['lat_cos'] = np.cos(processed['lat_rad'])
        processed['lon_sin'] = np.sin(processed['lon_rad'])
        processed['lon_cos'] = np.cos(processed['lon_rad'])
        
        # Temporal features
        processed['year_norm'] = (processed['year'] - processed['year'].min()) / (processed['year'].max() - processed['year'].min())
        processed['month_sin'] = np.sin(2 * np.pi * processed['month'] / 12)
        processed['month_cos'] = np.cos(2 * np.pi * processed['month'] / 12)
        
        # Log transform concentration (handle zeros)
        processed['log_concentration'] = np.log1p(processed['Microplastics measurement'])
        
        self.processed_data = processed
        self.logger.info(f"Prepared {len(processed)} records for modeling")
        
        return processed
    
    def create_spatial_temporal_grid(self, resolution: float = 1.0) -> pd.DataFrame:
        """
        Create a regular spatio-temporal grid for synthetic data generation
        
        Args:
            resolution: Grid resolution in degrees
            
        Returns:
            DataFrame with grid points
        """
        if self.processed_data is None:
            self.prepare_time_series_features()
        
        # Define spatial bounds
        lat_min, lat_max = self.processed_data['Latitude (degree)'].min(), self.processed_data['Latitude (degree)'].max()
        lon_min, lon_max = self.processed_data['Longitude(degree)'].min(), self.processed_data['Longitude(degree)'].max()
        
        # Create grid
        lats = np.arange(lat_min, lat_max + resolution, resolution)
        lons = np.arange(lon_min, lon_max + resolution, resolution)
        
        # Years for synthetic generation (extend to 2025)
        years = list(range(1993, 2026))
        months = list(range(1, 13))
        
        # Create grid combinations
        grid_points = []
        for year in years:
            for month in months:
                for lat in lats:
                    for lon in lons:
                        grid_points.append({
                            'year': year,
                            'month': month,
                            'Latitude (degree)': lat,
                            'Longitude(degree)': lon
                        })
        
        grid_df = pd.DataFrame(grid_points)
        
        # Add derived features
        grid_df['season'] = grid_df['month'].map({
            12: 'winter', 1: 'winter', 2: 'winter',
            3: 'spring', 4: 'spring', 5: 'spring',
            6: 'summer', 7: 'summer', 8: 'summer',
            9: 'fall', 10: 'fall', 11: 'fall'
        })
        
        # Coordinate transformations
        grid_df['lat_rad'] = np.radians(grid_df['Latitude (degree)'])
        grid_df['lon_rad'] = np.radians(grid_df['Longitude(degree)'])
        grid_df['lat_sin'] = np.sin(grid_df['lat_rad'])
        grid_df['lat_cos'] = np.cos(grid_df['lat_rad'])
        grid_df['lon_sin'] = np.sin(grid_df['lon_rad'])
        grid_df['lon_cos'] = np.cos(grid_df['lon_rad'])
        
        # Temporal features
        grid_df['year_norm'] = (grid_df['year'] - years[0]) / (years[-1] - years[0])
        grid_df['month_sin'] = np.sin(2 * np.pi * grid_df['month'] / 12)
        grid_df['month_cos'] = np.cos(2 * np.pi * grid_df['month'] / 12)
        
        self.logger.info(f"Created grid with {len(grid_df)} points")
        
        return grid_df
    
    def save_processed_data(self, data: pd.DataFrame, filename: str) -> str:
        """
        Save processed data to file
        
        Args:
            data: DataFrame to save
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        output_path = os.path.join(self.output_dir, filename)
        
        # Save as both CSV and pickle for flexibility
        data.to_csv(f"{output_path}.csv", index=False)
        data.to_pickle(f"{output_path}.pkl")
        
        self.logger.info(f"Saved processed data to {output_path}")
        
        return output_path
    
    def generate_analysis_report(self) -> Dict:
        """
        Generate comprehensive analysis report
        
        Returns:
            Dictionary with all analysis results
        """
        self.logger.info("Generating comprehensive analysis report...")
        
        # Load data if not already loaded
        if self.raw_data is None:
            self.load_data()
        
        # Perform all analyses
        temporal_analysis = self.analyze_temporal_coverage()
        spatial_analysis = self.analyze_spatial_coverage()
        concentration_analysis = self.analyze_concentration_patterns()
        
        # Prepare time series features
        processed_data = self.prepare_time_series_features()
        
        # Create report
        report = {
            'dataset_summary': {
                'total_records': len(self.raw_data),
                'processed_records': len(processed_data),
                'columns': list(self.raw_data.columns),
                'analysis_timestamp': datetime.now().isoformat()
            },
            'temporal_analysis': temporal_analysis,
            'spatial_analysis': spatial_analysis,
            'concentration_analysis': concentration_analysis,
            'data_quality': {
                'missing_coordinates': self.raw_data[['Latitude (degree)', 'Longitude(degree)']].isna().sum().to_dict(),
                'missing_concentrations': self.raw_data['Microplastics measurement'].isna().sum(),
                'data_completeness_pct': (1 - self.raw_data.isna().mean()).mean() * 100
            }
        }
        
        # Save report
        report_path = os.path.join(self.output_dir, 'microplastics_analysis_report.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Analysis report saved to {report_path}")
        
        return report


class SimplifiedGANSynthesizer:
    """
    Simplified GAN-based synthetic data generator for microplastics
    """
    
    def __init__(self, output_dir: str = None):
        """
        Initialize the GAN synthesizer
        
        Args:
            output_dir: Output directory for synthetic data
        """
        self.output_dir = output_dir or "/Volumes/Backup/panta-rhei-data-map/ocean-data/processed/unified_coords/microplastics"
        self.generator = None
        self.discriminator = None
        self.scaler = MinMaxScaler()
        self.feature_columns = []
        self.sequence_length = 6  # 6 months of data per sequence
        self.noise_dim = 100
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Create output directory
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def prepare_sequences(self, data: pd.DataFrame, features: List[str]) -> np.ndarray:
        """
        Prepare time series sequences for TimeGAN training
        
        Args:
            data: Input DataFrame with time series data
            features: List of feature columns to use
            
        Returns:
            3D array of sequences (samples, timesteps, features)
        """
        self.feature_columns = features
        
        # Sort by time
        data_sorted = data.sort_values(['year', 'month']).copy()
        
        # Scale features
        feature_data = data_sorted[features].values
        scaled_data = self.scaler.fit_transform(feature_data)
        
        # Create sequences
        sequences = []
        for i in range(len(scaled_data) - self.sequence_length + 1):
            sequences.append(scaled_data[i:i + self.sequence_length])
        
        sequences_array = np.array(sequences)
        self.logger.info(f"Created {len(sequences_array)} sequences of length {self.sequence_length}")
        
        return sequences_array
    
    def build_generator(self, seq_len: int, feature_dim: int):
        """Build generator model"""
        model = keras.Sequential([
            layers.Dense(128, activation='relu', input_shape=(self.noise_dim,)),
            layers.BatchNormalization(),
            layers.Dense(256, activation='relu'),
            layers.BatchNormalization(),
            layers.Dense(seq_len * feature_dim, activation='tanh'),
            layers.Reshape((seq_len, feature_dim))
        ])
        return model
    
    def build_discriminator(self, seq_len: int, feature_dim: int):
        """Build discriminator model"""
        model = keras.Sequential([
            layers.Flatten(input_shape=(seq_len, feature_dim)),
            layers.Dense(256, activation='relu'),
            layers.Dropout(0.3),
            layers.Dense(128, activation='relu'),
            layers.Dropout(0.3),
            layers.Dense(1, activation='sigmoid')
        ])
        return model
    
    def train_gan(self, sequences: np.ndarray, epochs: int = 100) -> None:
        """
        Train simplified GAN model on sequences
        
        Args:
            sequences: 3D array of sequences
            epochs: Number of training epochs
        """
        self.logger.info(f"Training GAN on {sequences.shape[0]} sequences...")
        
        seq_len, feature_dim = sequences.shape[1], sequences.shape[2]
        
        # Build models
        self.generator = self.build_generator(seq_len, feature_dim)
        self.discriminator = self.build_discriminator(seq_len, feature_dim)
        
        # Compile discriminator
        self.discriminator.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        
        # Build and compile GAN
        self.discriminator.trainable = False
        gan_input = keras.Input(shape=(self.noise_dim,))
        gan_output = self.discriminator(self.generator(gan_input))
        self.gan = keras.Model(gan_input, gan_output)
        self.gan.compile(optimizer='adam', loss='binary_crossentropy')
        
        # Training loop
        batch_size = 32
        for epoch in range(epochs):
            # Train discriminator
            idx = np.random.randint(0, sequences.shape[0], batch_size)
            real_sequences = sequences[idx]
            
            noise = np.random.normal(0, 1, (batch_size, self.noise_dim))
            fake_sequences = self.generator.predict(noise, verbose=0)
            
            d_loss_real = self.discriminator.train_on_batch(real_sequences, np.ones((batch_size, 1)))
            d_loss_fake = self.discriminator.train_on_batch(fake_sequences, np.zeros((batch_size, 1)))
            
            # Train generator
            noise = np.random.normal(0, 1, (batch_size, self.noise_dim))
            g_loss = self.gan.train_on_batch(noise, np.ones((batch_size, 1)))
            
            if epoch % 10 == 0:
                self.logger.info(f"Epoch {epoch}: D_loss: {(d_loss_real[0] + d_loss_fake[0])/2:.4f}, G_loss: {g_loss:.4f}")
        
        self.logger.info("GAN training completed")
    
    def generate_synthetic_sequences(self, n_sequences: int) -> np.ndarray:
        """
        Generate synthetic sequences using trained GAN
        
        Args:
            n_sequences: Number of sequences to generate
            
        Returns:
            Generated synthetic sequences
        """
        if self.generator is None:
            raise ValueError("Model must be trained before generating synthetic data")
        
        self.logger.info(f"Generating {n_sequences} synthetic sequences...")
        
        # Generate synthetic data
        noise = np.random.normal(0, 1, (n_sequences, self.noise_dim))
        synthetic_sequences = self.generator.predict(noise, verbose=0)
        
        # Inverse transform to original scale
        synthetic_sequences_scaled = synthetic_sequences.reshape(-1, len(self.feature_columns))
        synthetic_sequences_original = self.scaler.inverse_transform(synthetic_sequences_scaled)
        synthetic_sequences = synthetic_sequences_original.reshape(synthetic_sequences.shape)
        
        self.logger.info("Synthetic sequence generation completed")
        
        return synthetic_sequences
    
    def sequences_to_dataframe(self, sequences: np.ndarray, start_year: int = 2024) -> pd.DataFrame:
        """
        Convert sequences back to DataFrame format
        
        Args:
            sequences: Generated sequences
            start_year: Starting year for synthetic data
            
        Returns:
            DataFrame with synthetic data
        """
        synthetic_data = []
        
        for seq_idx, sequence in enumerate(sequences):
            for time_idx, timestep in enumerate(sequence):
                year = start_year + (seq_idx * self.sequence_length + time_idx) // 12
                month = ((seq_idx * self.sequence_length + time_idx) % 12) + 1
                
                # Create record
                record = {'year': year, 'month': month}
                for feature_idx, feature_name in enumerate(self.feature_columns):
                    record[feature_name] = timestep[feature_idx]
                
                synthetic_data.append(record)
        
        synthetic_df = pd.DataFrame(synthetic_data)
        
        # Remove duplicates and sort
        synthetic_df = synthetic_df.drop_duplicates().sort_values(['year', 'month'])
        
        # Add derived features
        synthetic_df['season'] = synthetic_df['month'].map({
            12: 'winter', 1: 'winter', 2: 'winter',
            3: 'spring', 4: 'spring', 5: 'spring',
            6: 'summer', 7: 'summer', 8: 'summer',
            9: 'fall', 10: 'fall', 11: 'fall'
        })
        
        # Add date
        synthetic_df['Date (MM-DD-YYYY)'] = synthetic_df.apply(
            lambda row: f"{row['month']}/15/{int(row['year'])} 12:00:00 AM", axis=1
        )
        
        # Ensure realistic constraints
        if 'Microplastics measurement' in synthetic_df.columns:
            # Ensure non-negative concentrations
            synthetic_df['Microplastics measurement'] = np.maximum(0, synthetic_df['Microplastics measurement'])
            
            # Add concentration classes
            synthetic_df['Concentration class text'] = pd.cut(
                synthetic_df['Microplastics measurement'],
                bins=[0, 0.0005, 0.005, 1, 100, np.inf],
                labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'],
                include_lowest=True
            )
        
        self.logger.info(f"Generated {len(synthetic_df)} synthetic records")
        
        return synthetic_df
    
    def save_synthetic_data(self, synthetic_df: pd.DataFrame, filename: str) -> str:
        """
        Save synthetic data to file
        
        Args:
            synthetic_df: Synthetic DataFrame
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        output_path = os.path.join(self.output_dir, filename)
        
        # Save as CSV
        synthetic_df.to_csv(f"{output_path}.csv", index=False)
        
        # Save as pickle for later use
        synthetic_df.to_pickle(f"{output_path}.pkl")
        
        self.logger.info(f"Saved synthetic data to {output_path}")
        
        return output_path


class EnvironmentalConditioner:
    """
    Environmental conditioning system for realistic synthetic data
    """
    
    def __init__(self):
        """
        Initialize environmental conditioner
        """
        self.logger = logging.getLogger(__name__)
    
    def add_environmental_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Add environmental conditioning features
        
        Args:
            data: Input DataFrame
            
        Returns:
            DataFrame with environmental features
        """
        enhanced_data = data.copy()
        
        # Distance from major pollution sources (simplified model)
        # Major coastal cities coordinates (lat, lon)
        pollution_sources = [
            (40.7128, -74.0060),  # New York
            (34.0522, -118.2437), # Los Angeles  
            (51.5074, -0.1278),   # London
            (35.6762, 139.6503),  # Tokyo
            (31.2304, 121.4737),  # Shanghai
        ]
        
        def min_distance_to_pollution(lat, lon):
            """Calculate minimum distance to pollution sources"""
            distances = []
            for source_lat, source_lon in pollution_sources:
                # Simplified distance calculation
                dist = np.sqrt((lat - source_lat)**2 + (lon - source_lon)**2)
                distances.append(dist)
            return min(distances)
        
        # Add pollution proximity feature
        enhanced_data['pollution_proximity'] = enhanced_data.apply(
            lambda row: min_distance_to_pollution(
                row['Latitude (degree)'], row['Longitude(degree)']
            ), axis=1
        )
        
        # Normalize pollution proximity (closer = higher value)
        max_distance = enhanced_data['pollution_proximity'].max()
        enhanced_data['pollution_proximity_norm'] = 1 - (enhanced_data['pollution_proximity'] / max_distance)
        
        # Seasonal ocean productivity proxy
        enhanced_data['seasonal_productivity'] = enhanced_data.apply(
            lambda row: self._seasonal_productivity(row['month'], row['Latitude (degree)']), axis=1
        )
        
        # Ocean depth influence (if available)
        if 'Ocean Bottom Depth (m)' in enhanced_data.columns:
            # Shallow waters tend to have more microplastics
            enhanced_data['depth_factor'] = enhanced_data['Ocean Bottom Depth (m)'].apply(
                lambda x: 1 / (1 + x/1000) if pd.notna(x) else 0.5
            )
        else:
            enhanced_data['depth_factor'] = 0.5  # Default neutral value
        
        self.logger.info("Added environmental conditioning features")
        
        return enhanced_data
    
    def _seasonal_productivity(self, month: int, latitude: float) -> float:
        """
        Calculate seasonal ocean productivity factor
        
        Args:
            month: Month (1-12)
            latitude: Latitude in degrees
            
        Returns:
            Seasonal productivity factor (0-1)
        """
        # Northern hemisphere spring/summer bloom
        if latitude > 0:
            if month in [3, 4, 5, 6, 7, 8]:
                return 0.8
            else:
                return 0.3
        # Southern hemisphere opposite seasons
        else:
            if month in [9, 10, 11, 12, 1, 2]:
                return 0.8
            else:
                return 0.3


def main():
    """
    Main function to run the microplastics data analysis and synthesis
    """
    print("Microplastics Data Processor - Complete Pipeline")
    print("=" * 50)
    
    # Phase 1: Data Analysis
    print("\n[Phase 1] Data Analysis and Preprocessing")
    print("-" * 40)
    
    processor = MicroplasticsDataProcessor()
    
    try:
        # Generate comprehensive analysis
        report = processor.generate_analysis_report()
        
        print(f"\nDataset Summary:")
        print(f"- Total records: {report['dataset_summary']['total_records']:,}")
        print(f"- Processed records: {report['dataset_summary']['processed_records']:,}")
        print(f"- Temporal coverage: {report['temporal_analysis']['min_year']}-{report['temporal_analysis']['max_year']}")
        print(f"- Spatial coverage: {len(report['spatial_analysis']['ocean_distribution'])} oceans")
        print(f"- Mean concentration: {report['concentration_analysis']['mean']:.6f} pieces/m³")
        print(f"- Data completeness: {report['data_quality']['data_completeness_pct']:.1f}%")
        
        # Phase 2: Environmental Conditioning
        print("\n[Phase 2] Environmental Conditioning")
        print("-" * 40)
        
        # Prepare data for training (1993-2023)
        training_data = processor.prepare_time_series_features(target_years=list(range(1993, 2024)))
        
        # Add environmental features
        conditioner = EnvironmentalConditioner()
        enhanced_data = conditioner.add_environmental_features(training_data)
        
        # Select features for TimeGAN training
        model_features = [
            'Latitude (degree)', 'Longitude(degree)', 'year_norm', 'month_sin', 'month_cos',
            'log_concentration', 'pollution_proximity_norm', 'seasonal_productivity', 'depth_factor'
        ]
        
        # Filter features that actually exist in the data
        available_features = [f for f in model_features if f in enhanced_data.columns]
        print(f"Using {len(available_features)} features for modeling: {available_features}")
        
        # Phase 3: GAN Training
        print("\n[Phase 3] GAN Model Training")
        print("-" * 40)
        
        synthesizer = SimplifiedGANSynthesizer()
        
        # Prepare sequences for training
        sequences = synthesizer.prepare_sequences(enhanced_data, available_features)
        print(f"Training sequences shape: {sequences.shape}")
        
        # Train GAN model
        print("Starting GAN training (this may take several minutes)...")
        synthesizer.train_gan(sequences, epochs=30)  # Reasonable epochs for GAN training
        
        # Phase 4: Synthetic Data Generation
        print("\n[Phase 4] Synthetic Data Generation")
        print("-" * 40)
        
        # Generate synthetic sequences for 2024-2025
        n_synthetic_sequences = 50  # Generate 50 sequences for testing
        synthetic_sequences = synthesizer.generate_synthetic_sequences(n_synthetic_sequences)
        
        # Convert to DataFrame
        synthetic_df = synthesizer.sequences_to_dataframe(synthetic_sequences, start_year=2024)
        
        # Save synthetic data
        output_path = synthesizer.save_synthetic_data(
            synthetic_df, 
            f"microplastics_synthetic_2024_2025_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        print(f"\nSynthesis Complete!")
        print(f"- Generated {len(synthetic_df)} synthetic records")
        print(f"- Temporal coverage: 2024-2025")
        print(f"- Output saved to: {output_path}")
        
        # Generate summary statistics
        print(f"\nSynthetic Data Summary:")
        if 'Microplastics measurement' in synthetic_df.columns:
            print(f"- Mean concentration: {synthetic_df['Microplastics measurement'].mean():.6f} pieces/m³")
            print(f"- Median concentration: {synthetic_df['Microplastics measurement'].median():.6f} pieces/m³")
            print(f"- Concentration range: {synthetic_df['Microplastics measurement'].min():.6f} - {synthetic_df['Microplastics measurement'].max():.6f}")
        
        print(f"- Spatial coverage: {synthetic_df['Latitude (degree)'].min():.2f}° to {synthetic_df['Latitude (degree)'].max():.2f}° latitude")
        print(f"- Unique locations: {len(synthetic_df.groupby(['Latitude (degree)', 'Longitude(degree)']))}")
        
        return synthetic_df, report
        
    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()
        raise


def run_analysis_only():
    """
    Run only the data analysis phase (faster for testing)
    """
    print("Microplastics Data Processor - Analysis Only")
    print("=" * 50)
    
    processor = MicroplasticsDataProcessor()
    report = processor.generate_analysis_report()
    
    print(f"\nDataset Summary:")
    print(f"- Total records: {report['dataset_summary']['total_records']:,}")
    print(f"- Processed records: {report['dataset_summary']['processed_records']:,}")
    print(f"- Temporal coverage: {report['temporal_analysis']['min_year']}-{report['temporal_analysis']['max_year']}")
    print(f"- Mean concentration: {report['concentration_analysis']['mean']:.6f} pieces/m³")
    
    return report


if __name__ == "__main__":
    # Run the complete pipeline
    main()