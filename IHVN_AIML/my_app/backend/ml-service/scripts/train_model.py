#!/usr/bin/env python3
"""
Script to train IIT prediction model from JSON data directory
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from iit_training_pipeline import IITModelTrainer


def main():
    parser = argparse.ArgumentParser(
        description="Train IIT Prediction Model from JSON directory"
    )
    parser.add_argument(
        "json_directory",
        type=str,
        help="Directory containing patient JSON files"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./models",
        help="Output directory for model artifacts (default: ./models)"
    )
    
    args = parser.parse_args()
    
    # Validate input directory
    json_dir = Path(args.json_directory)
    if not json_dir.exists():
        print(f"Error: Directory {json_dir} does not exist")
        sys.exit(1)
    
    if not any(json_dir.glob("*.json")):
        print(f"Error: No JSON files found in {json_dir}")
        sys.exit(1)
    
    print(f"Training IIT model from: {json_dir}")
    print(f"Output directory: {args.output_dir}")
    
    # Train model
    trainer = IITModelTrainer(output_dir=args.output_dir)
    
    try:
        model, metrics, processed_data = trainer.train_from_json_directory(
            str(json_dir)
        )
        
        print("\n" + "="*60)
        print("Training completed successfully!")
        print("="*60)
        print(f"AUC: {metrics['auc']:.4f}")
        print(f"Precision: {metrics['precision']:.4f}")
        print(f"Recall: {metrics['recall']:.4f}")
        print(f"F1 Score: {metrics['f1']:.4f}")
        print(f"\nModel artifacts saved to: {args.output_dir}")
        
        # Save processed data
        output_csv = Path(args.output_dir) / "processed_patient_data.csv"
        processed_data.to_csv(output_csv, index=False)
        print(f"Processed data saved to: {output_csv}")
        
    except Exception as e:
        print(f"\nError during training: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
