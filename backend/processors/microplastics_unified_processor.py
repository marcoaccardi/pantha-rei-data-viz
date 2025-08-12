"""
Microplastics Unified Data Processor

This module creates a complete microplastics dataset combining:
- Real data from 1993-2019 (NOAA dataset)
- Synthetic data from 2019-2025 (GAN-generated)
- Seamless integration with coordinate harmonization
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error
from datetime import datetime, timedelta
import os
import json
import logging
import xarray as xr
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
import warnings
warnings.filterwarnings('ignore')

# ML imports for synthetic generation
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

# Import existing coordinate harmonizer
try:
    from .coordinate_harmonizer import CoordinateHarmonizer
except ImportError:
    from coordinate_harmonizer import CoordinateHarmonizer


class MicroplasticsUnifiedProcessor:
    """
    Unified processor for microplastics data combining real and synthetic sources
    """
    
    def __init__(self, 
                 data_path: str = None, 
                 output_dir: str = None,
                 real_data_years: Tuple[int, int] = (1993, 2019),
                 synthetic_data_years: Tuple[int, int] = (2019, 2025)):
        """
        Initialize the unified processor
        
        Args:
            data_path: Path to the NOAA microplastics CSV file
            output_dir: Output directory for processed data
            real_data_years: Tuple of (start_year, end_year) for real data
            synthetic_data_years: Tuple of (start_year, end_year) for synthetic data
        """
        self.data_path = data_path or "/Users/marco/Downloads/Marine_Microplastics_WGS84_8553846406879449657.csv"
        self.output_dir = output_dir or "../ocean-data/processed/unified_coords/microplastics"
        
        # Data period definitions
        self.real_years = real_data_years
        self.synthetic_years = synthetic_data_years
        
        # Data storage
        self.raw_data = None
        self.real_data = None
        self.synthetic_data = None
        self.unified_data = None
        
        # Models and scalers
        self.gan_generator = None
        self.gan_discriminator = None
        self.scaler = MinMaxScaler()
        self.feature_columns = []
        
        # Configuration
        self.sequence_length = 12  # 12 months
        self.noise_dim = 100
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Create output directories
        self._setup_directories()
        
        # Initialize coordinate harmonizer
        self.harmonizer = CoordinateHarmonizer()
    
    def _setup_directories(self):
        """Create necessary output directories"""
        directories = [
            self.output_dir,
            os.path.join(self.output_dir, 'real'),
            os.path.join(self.output_dir, 'synthetic'), 
            os.path.join(self.output_dir, 'unified'),
            os.path.join(self.output_dir, 'textures')
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Created output directory structure")
    
    def load_and_analyze_data(self) -> Dict:
        """
        Load raw data and perform comprehensive analysis
        
        Returns:
            Analysis report dictionary
        """
        self.logger.info("Loading and analyzing raw microplastics data...")
        
        # Load CSV with proper encoding
        self.raw_data = pd.read_csv(self.data_path, encoding='utf-8-sig')
        
        # Clean column names
        self.raw_data.columns = [col.strip().replace('\ufeff', '') for col in self.raw_data.columns]
        
        # Parse dates
        date_col = 'Date (MM-DD-YYYY)'
        self.raw_data['parsed_date'] = pd.to_datetime(self.raw_data[date_col], errors='coerce')
        self.raw_data['year'] = self.raw_data['parsed_date'].dt.year
        self.raw_data['month'] = self.raw_data['parsed_date'].dt.month
        
        # Remove invalid dates and concentrations
        self.raw_data = self.raw_data.dropna(subset=['parsed_date', 'Microplastics measurement'])
        
        # Analysis summary
        analysis = {
            'total_records': len(self.raw_data),
            'date_range': (self.raw_data['year'].min(), self.raw_data['year'].max()),
            'real_data_available': len(self.raw_data[
                (self.raw_data['year'] >= self.real_years[0]) & 
                (self.raw_data['year'] <= self.real_years[1])
            ]),
            'spatial_coverage': {
                'lat_range': (self.raw_data['Latitude (degree)'].min(), 
                             self.raw_data['Latitude (degree)'].max()),
                'lon_range': (self.raw_data['Longitude(degree)'].min(), 
                             self.raw_data['Longitude(degree)'].max())
            },
            'concentration_stats': {
                'mean': self.raw_data['Microplastics measurement'].mean(),
                'median': self.raw_data['Microplastics measurement'].median(),
                'std': self.raw_data['Microplastics measurement'].std(),
                'zero_pct': (self.raw_data['Microplastics measurement'] == 0).mean() * 100
            }
        }
        
        self.logger.info(f"Data analysis complete: {analysis['total_records']} total records, "
                        f"{analysis['real_data_available']} available for real data period")
        
        return analysis
    
    def extract_real_data(self) -> pd.DataFrame:
        """
        Extract and process real data for 1993-2019 period
        
        Returns:
            Cleaned real data DataFrame
        """
        self.logger.info(f"Extracting real data for {self.real_years[0]}-{self.real_years[1]}...")
        
        if self.raw_data is None:
            self.load_and_analyze_data()
        
        # Filter data for real period
        real_mask = (
            (self.raw_data['year'] >= self.real_years[0]) & 
            (self.raw_data['year'] <= self.real_years[1])
        )
        self.real_data = self.raw_data[real_mask].copy()
        
        # Add derived features
        self.real_data = self._add_derived_features(self.real_data)
        
        # Add data source flag
        self.real_data['data_source'] = 'real'
        self.real_data['confidence'] = 1.0  # High confidence for real data
        
        # Save real data
        real_output_path = os.path.join(self.output_dir, 'real', 'microplastics_1993_2019.csv')
        self.real_data.to_csv(real_output_path, index=False)
        
        self.logger.info(f"Extracted {len(self.real_data)} real data records and saved to {real_output_path}")
        
        return self.real_data
    
    def _add_derived_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Add derived features for modeling and analysis
        
        Args:
            data: Input DataFrame
            
        Returns:
            DataFrame with added features
        """
        enhanced_data = data.copy()
        
        # Temporal features
        enhanced_data['season'] = enhanced_data['month'].map({
            12: 'winter', 1: 'winter', 2: 'winter',
            3: 'spring', 4: 'spring', 5: 'spring',
            6: 'summer', 7: 'summer', 8: 'summer',
            9: 'fall', 10: 'fall', 11: 'fall'
        })
        
        # Normalized temporal features
        year_min, year_max = enhanced_data['year'].min(), enhanced_data['year'].max()
        enhanced_data['year_norm'] = (enhanced_data['year'] - year_min) / (year_max - year_min)
        enhanced_data['month_sin'] = np.sin(2 * np.pi * enhanced_data['month'] / 12)
        enhanced_data['month_cos'] = np.cos(2 * np.pi * enhanced_data['month'] / 12)
        
        # Coordinate transformations
        enhanced_data['lat_rad'] = np.radians(enhanced_data['Latitude (degree)'])
        enhanced_data['lon_rad'] = np.radians(enhanced_data['Longitude(degree)'])
        enhanced_data['lat_sin'] = np.sin(enhanced_data['lat_rad'])
        enhanced_data['lat_cos'] = np.cos(enhanced_data['lat_rad'])
        enhanced_data['lon_sin'] = np.sin(enhanced_data['lon_rad'])
        enhanced_data['lon_cos'] = np.cos(enhanced_data['lon_rad'])
        
        # Log-transformed concentration (handle zeros)
        enhanced_data['log_concentration'] = np.log1p(enhanced_data['Microplastics measurement'])
        
        # Environmental conditioning features
        enhanced_data = self._add_environmental_features(enhanced_data)
        
        return enhanced_data
    
    def _add_environmental_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add environmental conditioning features"""
        enhanced_data = data.copy()
        
        # Major pollution sources (coastal megacities)
        pollution_sources = [
            (40.7128, -74.0060),   # New York
            (34.0522, -118.2437),  # Los Angeles  
            (51.5074, -0.1278),    # London
            (35.6762, 139.6503),   # Tokyo
            (31.2304, 121.4737),   # Shanghai
            (22.3193, 114.1694),   # Hong Kong
            (1.3521, 103.8198),    # Singapore
            (-33.8688, 151.2093),  # Sydney
        ]
        
        def min_distance_to_pollution(lat, lon):
            """Calculate minimum distance to pollution sources"""
            distances = []
            for source_lat, source_lon in pollution_sources:
                # Haversine distance approximation
                dlat = np.radians(lat - source_lat)
                dlon = np.radians(lon - source_lon)
                a = np.sin(dlat/2)**2 + np.cos(np.radians(source_lat)) * np.cos(np.radians(lat)) * np.sin(dlon/2)**2
                distance = 2 * np.arcsin(np.sqrt(a)) * 6371  # Earth radius in km
                distances.append(distance)
            return min(distances)
        
        # Calculate pollution proximity
        enhanced_data['pollution_distance'] = enhanced_data.apply(
            lambda row: min_distance_to_pollution(row['Latitude (degree)'], row['Longitude(degree)']), 
            axis=1
        )
        
        # Normalize (closer = higher value, max distance ~20000km)
        enhanced_data['pollution_proximity'] = 1 - (enhanced_data['pollution_distance'] / 20000)
        enhanced_data['pollution_proximity'] = np.clip(enhanced_data['pollution_proximity'], 0, 1)
        
        # Seasonal productivity (simplified model)
        def seasonal_productivity(month, latitude):
            """Calculate seasonal ocean productivity factor"""
            if latitude > 0:  # Northern hemisphere
                if month in [3, 4, 5, 6, 7, 8]:  # Spring/summer
                    return 0.8
                else:
                    return 0.3
            else:  # Southern hemisphere (opposite seasons)
                if month in [9, 10, 11, 12, 1, 2]:  # Spring/summer
                    return 0.8
                else:
                    return 0.3
        
        enhanced_data['seasonal_productivity'] = enhanced_data.apply(
            lambda row: seasonal_productivity(row['month'], row['Latitude (degree)']), 
            axis=1
        )
        
        # Ocean depth influence (shallow = more microplastics)
        if 'Ocean Bottom Depth (m)' in enhanced_data.columns:
            enhanced_data['depth_factor'] = enhanced_data['Ocean Bottom Depth (m)'].apply(
                lambda x: 1 / (1 + x/1000) if pd.notna(x) and x > 0 else 0.5
            )
        else:
            enhanced_data['depth_factor'] = 0.5
        
        # Coastal proximity (distance to nearest coast - simplified)
        def coastal_proximity(lat, lon):
            """Simplified coastal proximity based on major landmass centers"""
            # This is a simplified model - in practice you'd use actual coastline data
            land_centers = [
                (39.8283, -98.5795),  # North America center
                (54.5260, -105.2551), # Canada center  
                (56.1304, -106.3468), # Europe center
                (-25.2744, 133.7751), # Australia center
                (20.5937, 78.9629),   # Asia center
                (-8.7832, -55.4915),  # South America center
                (1.6508, 10.2679),    # Africa center
            ]
            
            min_dist = float('inf')
            for land_lat, land_lon in land_centers:
                dlat = np.radians(lat - land_lat)
                dlon = np.radians(lon - land_lon)
                a = np.sin(dlat/2)**2 + np.cos(np.radians(land_lat)) * np.cos(np.radians(lat)) * np.sin(dlon/2)**2
                distance = 2 * np.arcsin(np.sqrt(a)) * 6371
                min_dist = min(min_dist, distance)
            
            # Convert to proximity (closer = higher value)
            return 1 / (1 + min_dist/1000)
        
        enhanced_data['coastal_proximity'] = enhanced_data.apply(
            lambda row: coastal_proximity(row['Latitude (degree)'], row['Longitude(degree)']), 
            axis=1
        )
        
        return enhanced_data
    
    def build_enhanced_generator(self, seq_len: int, feature_dim: int):
        """Build enhanced LSTM-GAN generator"""
        model = keras.Sequential([
            # Dense layers for initial processing
            layers.Dense(128, activation='relu', input_shape=(self.noise_dim,)),
            layers.BatchNormalization(),
            layers.Dropout(0.2),
            
            layers.Dense(256, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.2),
            
            # Reshape for LSTM
            layers.Dense(seq_len * 64),
            layers.Reshape((seq_len, 64)),
            
            # LSTM layers for temporal modeling
            layers.LSTM(128, return_sequences=True),
            layers.BatchNormalization(),
            
            layers.LSTM(64, return_sequences=True),
            layers.BatchNormalization(),
            
            # Final output layer
            layers.Dense(feature_dim, activation='tanh')
        ])
        
        return model
    
    def build_enhanced_discriminator(self, seq_len: int, feature_dim: int):
        """Build enhanced LSTM-GAN discriminator"""
        model = keras.Sequential([
            # LSTM layers for temporal pattern recognition
            layers.LSTM(64, return_sequences=True, input_shape=(seq_len, feature_dim)),
            layers.Dropout(0.3),
            
            layers.LSTM(32, return_sequences=False),
            layers.Dropout(0.3),
            
            # Dense layers for classification
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.3),
            
            layers.Dense(32, activation='relu'),
            layers.Dropout(0.3),
            
            layers.Dense(1, activation='sigmoid')
        ])
        
        return model
    
    def train_enhanced_gan(self, training_data: pd.DataFrame, epochs: int = 100) -> Dict:
        """
        Train enhanced GAN model on real data
        
        Args:
            training_data: Real data for training
            epochs: Number of training epochs
            
        Returns:
            Training metrics dictionary
        """
        self.logger.info(f"Training enhanced GAN on {len(training_data)} records...")
        
        # Prepare training sequences
        sequences = self._prepare_training_sequences(training_data)
        
        if len(sequences) < 10:
            raise ValueError(f"Insufficient data for training: {len(sequences)} sequences")
        
        seq_len, feature_dim = sequences.shape[1], sequences.shape[2]
        self.logger.info(f"Training sequences shape: {sequences.shape}")
        
        # Build models
        self.gan_generator = self.build_enhanced_generator(seq_len, feature_dim)
        self.gan_discriminator = self.build_enhanced_discriminator(seq_len, feature_dim)
        
        # Compile discriminator
        self.gan_discriminator.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.0002, beta_1=0.5),
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        
        # Build and compile GAN
        self.gan_discriminator.trainable = False
        gan_input = keras.Input(shape=(self.noise_dim,))
        gan_output = self.gan_discriminator(self.gan_generator(gan_input))
        self.gan = keras.Model(gan_input, gan_output)
        self.gan.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.0002, beta_1=0.5),
            loss='binary_crossentropy'
        )
        
        # Training metrics
        training_metrics = {
            'd_losses': [],
            'g_losses': [],
            'd_accuracies': []
        }
        
        # Training loop
        batch_size = min(32, len(sequences) // 4)
        for epoch in range(epochs):
            # Train discriminator
            idx = np.random.randint(0, sequences.shape[0], batch_size)
            real_sequences = sequences[idx]
            
            noise = np.random.normal(0, 1, (batch_size, self.noise_dim))
            fake_sequences = self.gan_generator.predict(noise, verbose=0)
            
            # Train on real data
            d_loss_real = self.gan_discriminator.train_on_batch(
                real_sequences, np.ones((batch_size, 1)) * 0.9  # Label smoothing
            )
            
            # Train on fake data
            d_loss_fake = self.gan_discriminator.train_on_batch(
                fake_sequences, np.zeros((batch_size, 1))
            )
            
            # Train generator
            noise = np.random.normal(0, 1, (batch_size, self.noise_dim))
            g_loss = self.gan.train_on_batch(noise, np.ones((batch_size, 1)))
            
            # Record metrics
            d_loss = (d_loss_real[0] + d_loss_fake[0]) / 2
            d_acc = (d_loss_real[1] + d_loss_fake[1]) / 2
            
            training_metrics['d_losses'].append(d_loss)
            training_metrics['g_losses'].append(g_loss)
            training_metrics['d_accuracies'].append(d_acc)
            
            if epoch % 20 == 0:
                self.logger.info(f"Epoch {epoch}: D_loss: {d_loss:.4f}, G_loss: {g_loss:.4f}, D_acc: {d_acc:.4f}")
        
        self.logger.info("Enhanced GAN training completed")
        
        return training_metrics
    
    def _prepare_training_sequences(self, data: pd.DataFrame) -> np.ndarray:
        """Prepare sequences for GAN training"""
        # Select features for modeling
        model_features = [
            'Latitude (degree)', 'Longitude(degree)', 'year_norm', 'month_sin', 'month_cos',
            'log_concentration', 'pollution_proximity', 'seasonal_productivity', 
            'depth_factor', 'coastal_proximity'
        ]
        
        # Filter available features
        available_features = [f for f in model_features if f in data.columns]
        self.feature_columns = available_features
        
        # Sort by time and location
        data_sorted = data.sort_values(['year', 'month', 'Latitude (degree)', 'Longitude(degree)'])
        
        # Extract feature data
        feature_data = data_sorted[available_features].values
        
        # Scale features
        scaled_data = self.scaler.fit_transform(feature_data)
        
        # Create sequences
        sequences = []
        for i in range(len(scaled_data) - self.sequence_length + 1):
            sequences.append(scaled_data[i:i + self.sequence_length])
        
        return np.array(sequences)
    
    def generate_synthetic_data(self, n_years: int = 6) -> pd.DataFrame:
        """
        Generate synthetic data for the specified period
        
        Args:
            n_years: Number of years to generate
            
        Returns:
            Synthetic data DataFrame
        """
        if self.gan_generator is None:
            raise ValueError("GAN model must be trained before generating synthetic data")
        
        self.logger.info(f"Generating synthetic data for {n_years} years...")
        
        # Calculate number of sequences needed
        months_to_generate = n_years * 12
        n_sequences = max(100, months_to_generate * 2)  # Generate extra for diversity
        
        # Generate synthetic sequences
        noise = np.random.normal(0, 1, (n_sequences, self.noise_dim))
        synthetic_sequences = self.gan_generator.predict(noise, verbose=0)
        
        # Convert back to original scale
        synthetic_sequences_reshaped = synthetic_sequences.reshape(-1, len(self.feature_columns))
        synthetic_sequences_original = self.scaler.inverse_transform(synthetic_sequences_reshaped)
        synthetic_sequences = synthetic_sequences_original.reshape(synthetic_sequences.shape)
        
        # Convert sequences to DataFrame
        synthetic_records = []
        
        for seq_idx, sequence in enumerate(synthetic_sequences):
            for time_idx, timestep in enumerate(sequence):
                # Calculate year and month
                total_months = seq_idx * self.sequence_length + time_idx
                year = self.synthetic_years[0] + (total_months // 12)
                month = (total_months % 12) + 1
                
                # Stop if we've reached the end year
                if year > self.synthetic_years[1]:
                    break
                
                # Create record
                record = {
                    'year': year,
                    'month': month,
                    'Date (MM-DD-YYYY)': f"{month}/15/{year} 12:00:00 AM",
                    'data_source': 'synthetic',
                    'confidence': 0.7  # Lower confidence for synthetic data
                }
                
                # Add feature values
                for feature_idx, feature_name in enumerate(self.feature_columns):
                    record[feature_name] = timestep[feature_idx]
                
                synthetic_records.append(record)
        
        # Create DataFrame
        self.synthetic_data = pd.DataFrame(synthetic_records)
        
        # Remove duplicates and sort
        self.synthetic_data = self.synthetic_data.drop_duplicates(
            subset=['year', 'month', 'Latitude (degree)', 'Longitude(degree)']
        ).sort_values(['year', 'month'])
        
        # Apply post-processing
        self.synthetic_data = self._post_process_synthetic_data(self.synthetic_data)
        
        # Save synthetic data
        synthetic_output_path = os.path.join(
            self.output_dir, 'synthetic', f'microplastics_{self.synthetic_years[0]}_{self.synthetic_years[1]}_synthetic.csv'
        )
        self.synthetic_data.to_csv(synthetic_output_path, index=False)
        
        self.logger.info(f"Generated {len(self.synthetic_data)} synthetic records and saved to {synthetic_output_path}")
        
        return self.synthetic_data
    
    def _post_process_synthetic_data(self, synthetic_data: pd.DataFrame) -> pd.DataFrame:
        """Apply post-processing to synthetic data"""
        processed_data = synthetic_data.copy()
        
        # Ensure realistic coordinate bounds
        processed_data['Latitude (degree)'] = np.clip(
            processed_data['Latitude (degree)'], -90, 90
        )
        processed_data['Longitude(degree)'] = np.clip(
            processed_data['Longitude(degree)'], -180, 180
        )
        
        # Convert log_concentration back to actual concentration
        if 'log_concentration' in processed_data.columns:
            processed_data['Microplastics measurement'] = np.expm1(
                processed_data['log_concentration']
            )
            # Ensure non-negative concentrations
            processed_data['Microplastics measurement'] = np.maximum(
                0, processed_data['Microplastics measurement']
            )
        
        # Add concentration classes
        if 'Microplastics measurement' in processed_data.columns:
            processed_data['Concentration class text'] = pd.cut(
                processed_data['Microplastics measurement'],
                bins=[0, 0.0005, 0.005, 1, 100, np.inf],
                labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'],
                include_lowest=True
            )
            
            processed_data['Concentration class range'] = pd.cut(
                processed_data['Microplastics measurement'],
                bins=[0, 0.0005, 0.005, 1, 100, np.inf],
                labels=['0-0.0005', '0.0005-0.005', '0.005-1', '1-100', '100+'],
                include_lowest=True
            )
        
        # Add standard metadata
        processed_data['Unit'] = 'pieces/m3'
        processed_data['Ocean'] = 'Global Ocean'  # Simplified
        processed_data['Sampling Method'] = 'Synthetic Generation'
        processed_data['ORGANIZATION'] = 'GAN Model'
        processed_data['Long Reference'] = 'Synthetic data generated from GAN trained on NOAA microplastics dataset'
        
        return processed_data
    
    def create_unified_dataset(self) -> pd.DataFrame:
        """
        Create unified dataset combining real and synthetic data
        
        Returns:
            Unified DataFrame
        """
        self.logger.info("Creating unified dataset...")
        
        if self.real_data is None or self.synthetic_data is None:
            raise ValueError("Both real and synthetic data must be available")
        
        # Align column schemas
        self.synthetic_data = self._align_schemas(self.real_data, self.synthetic_data)
        
        # Combine datasets
        self.unified_data = pd.concat([self.real_data, self.synthetic_data], ignore_index=True)
        
        # Sort by date
        self.unified_data = self.unified_data.sort_values(['year', 'month'])
        
        # Add unified metadata
        self.unified_data['dataset_version'] = f"unified_{datetime.now().strftime('%Y%m%d')}"
        
        # Apply coordinate harmonization
        self.unified_data = self._apply_coordinate_harmonization(self.unified_data)
        
        # Save unified dataset
        unified_output_path = os.path.join(
            self.output_dir, 'unified', 'microplastics_complete_1993_2025.csv'
        )
        self.unified_data.to_csv(unified_output_path, index=False)
        
        self.logger.info(f"Created unified dataset with {len(self.unified_data)} records, saved to {unified_output_path}")
        
        return self.unified_data
    
    def _align_schemas(self, real_data: pd.DataFrame, synthetic_data: pd.DataFrame) -> pd.DataFrame:
        """Align synthetic data schema with real data"""
        aligned_synthetic = synthetic_data.copy()
        
        # Add missing columns from real data with default values
        for col in real_data.columns:
            if col not in aligned_synthetic.columns:
                if col in ['OBJECTID']:
                    # Generate sequential IDs for synthetic data
                    aligned_synthetic[col] = range(
                        real_data['OBJECTID'].max() + 1,
                        real_data['OBJECTID'].max() + 1 + len(aligned_synthetic)
                    )
                elif col in ['parsed_date']:
                    # Parse date from existing date column
                    aligned_synthetic[col] = pd.to_datetime(aligned_synthetic['Date (MM-DD-YYYY)'], errors='coerce')
                else:
                    # Fill with appropriate defaults
                    aligned_synthetic[col] = None
        
        # Reorder columns to match real data
        column_order = real_data.columns.tolist()
        # Add any new synthetic-only columns at the end
        for col in aligned_synthetic.columns:
            if col not in column_order:
                column_order.append(col)
        
        aligned_synthetic = aligned_synthetic.reindex(columns=column_order)
        
        return aligned_synthetic
    
    def _apply_coordinate_harmonization(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply coordinate harmonization using existing harmonizer"""
        harmonized_data = data.copy()
        
        # Normalize longitude to -180 to 180 range
        def normalize_longitude(lon):
            """Normalize longitude to -180 to 180 range"""
            lon = np.array(lon)
            return ((lon + 180) % 360) - 180
        
        # Apply longitude normalization
        harmonized_data['Longitude(degree)'] = normalize_longitude(
            harmonized_data['Longitude(degree)'].values
        )
        
        # Ensure latitude is within valid bounds
        harmonized_data['Latitude (degree)'] = np.clip(
            harmonized_data['Latitude (degree)'], -90, 90
        )
        
        # Add harmonized coordinate columns
        harmonized_data['longitude_harmonized'] = harmonized_data['Longitude(degree)']
        harmonized_data['latitude_harmonized'] = harmonized_data['Latitude (degree)']
        
        self.logger.info("Applied coordinate harmonization")
        
        return harmonized_data
    
    def generate_quality_report(self) -> Dict:
        """
        Generate comprehensive quality assessment report
        
        Returns:
            Quality report dictionary
        """
        if self.unified_data is None:
            raise ValueError("Unified dataset must be created first")
        
        self.logger.info("Generating quality assessment report...")
        
        # Separate data by source
        real_subset = self.unified_data[self.unified_data['data_source'] == 'real']
        synthetic_subset = self.unified_data[self.unified_data['data_source'] == 'synthetic']
        
        # Statistical comparison
        quality_metrics = {
            'data_coverage': {
                'total_records': len(self.unified_data),
                'real_records': len(real_subset),
                'synthetic_records': len(synthetic_subset),
                'temporal_coverage': f"{self.unified_data['year'].min()}-{self.unified_data['year'].max()}",
                'real_coverage': f"{real_subset['year'].min()}-{real_subset['year'].max()}",
                'synthetic_coverage': f"{synthetic_subset['year'].min()}-{synthetic_subset['year'].max()}"
            },
            'concentration_comparison': {
                'real_mean': real_subset['Microplastics measurement'].mean(),
                'synthetic_mean': synthetic_subset['Microplastics measurement'].mean(),
                'real_median': real_subset['Microplastics measurement'].median(),
                'synthetic_median': synthetic_subset['Microplastics measurement'].median(),
                'real_std': real_subset['Microplastics measurement'].std(),
                'synthetic_std': synthetic_subset['Microplastics measurement'].std()
            },
            'spatial_coverage': {
                'real_lat_range': (real_subset['Latitude (degree)'].min(), real_subset['Latitude (degree)'].max()),
                'synthetic_lat_range': (synthetic_subset['Latitude (degree)'].min(), synthetic_subset['Latitude (degree)'].max()),
                'real_lon_range': (real_subset['Longitude(degree)'].min(), real_subset['Longitude(degree)'].max()),
                'synthetic_lon_range': (synthetic_subset['Longitude(degree)'].min(), synthetic_subset['Longitude(degree)'].max())
            },
            'data_quality_flags': {
                'unrealistic_coordinates': len(self.unified_data[
                    (self.unified_data['Latitude (degree)'].abs() > 90) |
                    (self.unified_data['Longitude(degree)'].abs() > 180)
                ]),
                'negative_concentrations': len(self.unified_data[
                    self.unified_data['Microplastics measurement'] < 0
                ]),
                'missing_concentrations': self.unified_data['Microplastics measurement'].isna().sum()
            }
        }
        
        # Save quality report
        quality_report_path = os.path.join(self.output_dir, 'unified', 'quality_assessment_report.json')
        with open(quality_report_path, 'w') as f:
            json.dump(quality_metrics, f, indent=2, default=str)
        
        self.logger.info(f"Quality assessment report saved to {quality_report_path}")
        
        return quality_metrics
    
    def save_to_netcdf(self, output_filename: str = None) -> str:
        """
        Save unified dataset to NetCDF format for integration with ocean data system
        
        Args:
            output_filename: Optional custom filename
            
        Returns:
            Path to saved NetCDF file
        """
        if self.unified_data is None:
            raise ValueError("Unified dataset must be created first")
        
        if output_filename is None:
            output_filename = 'microplastics_complete_1993_2025.nc'
        
        output_path = os.path.join(self.output_dir, 'unified', output_filename)
        
        self.logger.info(f"Saving unified dataset to NetCDF format: {output_path}")
        
        # Create xarray dataset
        ds = xr.Dataset({
            'microplastics_concentration': (
                ['time'], 
                self.unified_data['Microplastics measurement'].values
            ),
            'latitude': (
                ['time'], 
                self.unified_data['Latitude (degree)'].values
            ),
            'longitude': (
                ['time'], 
                self.unified_data['Longitude(degree)'].values
            ),
            'data_source': (
                ['time'], 
                self.unified_data['data_source'].values
            ),
            'confidence': (
                ['time'], 
                self.unified_data['confidence'].values
            )
        }, coords={
            'time': pd.to_datetime(self.unified_data['Date (MM-DD-YYYY)'])
        })
        
        # Add metadata
        ds.attrs = {
            'title': 'Unified Microplastics Dataset 1993-2025',
            'description': 'Combined real and synthetic microplastics data for global oceans',
            'real_data_period': f"{self.real_years[0]}-{self.real_years[1]}",
            'synthetic_data_period': f"{self.synthetic_years[0]}-{self.synthetic_years[1]}",
            'creation_date': datetime.now().isoformat(),
            'total_records': len(self.unified_data),
            'real_records': len(self.unified_data[self.unified_data['data_source'] == 'real']),
            'synthetic_records': len(self.unified_data[self.unified_data['data_source'] == 'synthetic'])
        }
        
        # Save to NetCDF
        ds.to_netcdf(output_path)
        
        self.logger.info(f"NetCDF file saved successfully: {output_path}")
        
        return output_path


def main():
    """
    Main function to run the complete unified processing pipeline
    """
    print("Microplastics Unified Data Processor")
    print("=" * 50)
    
    # Initialize processor
    processor = MicroplasticsUnifiedProcessor()
    
    try:
        # Phase 1: Load and analyze data
        print("\n[Phase 1] Data Loading and Analysis")
        print("-" * 40)
        analysis = processor.load_and_analyze_data()
        print(f"Total records available: {analysis['total_records']:,}")
        print(f"Real data period: {analysis['real_data_available']:,} records available")
        
        # Phase 2: Extract real data
        print("\n[Phase 2] Real Data Extraction (1993-2019)")
        print("-" * 40)  
        real_data = processor.extract_real_data()
        print(f"Extracted {len(real_data):,} real data records")
        
        # Phase 3: Train GAN model
        print("\n[Phase 3] Enhanced GAN Training")
        print("-" * 40)
        training_metrics = processor.train_enhanced_gan(real_data, epochs=100)
        print(f"GAN training completed - Final D_loss: {training_metrics['d_losses'][-1]:.4f}")
        
        # Phase 4: Generate synthetic data
        print("\n[Phase 4] Synthetic Data Generation (2019-2025)")
        print("-" * 40)
        synthetic_data = processor.generate_synthetic_data(n_years=6)
        print(f"Generated {len(synthetic_data):,} synthetic records")
        
        # Phase 5: Create unified dataset
        print("\n[Phase 5] Unified Dataset Creation")
        print("-" * 40)
        unified_data = processor.create_unified_dataset()
        print(f"Created unified dataset with {len(unified_data):,} total records")
        
        # Phase 6: Quality assessment
        print("\n[Phase 6] Quality Assessment")
        print("-" * 40)
        quality_report = processor.generate_quality_report()
        print(f"Real data concentration mean: {quality_report['concentration_comparison']['real_mean']:.6f}")
        print(f"Synthetic data concentration mean: {quality_report['concentration_comparison']['synthetic_mean']:.6f}")
        
        # Phase 7: Save to NetCDF
        print("\n[Phase 7] NetCDF Export")
        print("-" * 40)
        netcdf_path = processor.save_to_netcdf()
        print(f"NetCDF file saved: {netcdf_path}")
        
        print(f"\n🎉 Processing Complete!")
        print(f"📊 Dataset Summary:")
        print(f"   - Total records: {len(unified_data):,}")
        print(f"   - Real data (1993-2019): {len(real_data):,} records")
        print(f"   - Synthetic data (2019-2025): {len(synthetic_data):,} records") 
        print(f"   - Temporal coverage: 33 years (1993-2025)")
        print(f"   - Output directory: {processor.output_dir}")
        
        return unified_data, quality_report
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()