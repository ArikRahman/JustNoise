#!/usr/bin/env python3
"""
Quick test script to verify Silero VAD installation and basic functionality.

Usage:
  python test_vad.py
"""

import sys

def test_imports():
    """Test that all required libraries are installed."""
    print("Testing imports...")
    
    try:
        import torch
        print(f"✓ PyTorch {torch.__version__}")
    except ImportError:
        print("✗ PyTorch not installed. Run: just setup-vad")
        return False
    
    try:
        import torchaudio
        print(f"✓ torchaudio {torchaudio.__version__}")
    except ImportError:
        print("✗ torchaudio not installed. Run: just setup-vad")
        return False
    
    try:
        import numpy as np
        print(f"✓ numpy {np.__version__}")
    except ImportError:
        print("✗ numpy not installed")
        return False
    
    return True


def test_model_load():
    """Test loading the Silero VAD model."""
    print("\nTesting Silero VAD model loading...")
    
    try:
        import torch
        
        print("  Downloading/loading model from PyTorch Hub...")
        model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False,
            trust_repo=True
        )
        
        print("✓ Silero VAD model loaded successfully")
        print(f"  Model device: {next(model.parameters()).device}")
        
        # Test basic inference with correct chunk size
        print("\nTesting inference on dummy audio...")
        import numpy as np
        
        # Create 512 samples of silence (required for 16kHz)
        dummy_audio = np.zeros(512, dtype=np.float32)
        audio_tensor = torch.from_numpy(dummy_audio)
        
        # Get VAD probability
        with torch.no_grad():
            speech_prob = model(audio_tensor, 16000).item()
        
        print(f"✓ Inference successful (silence probability: {speech_prob:.3f})")
        
        if speech_prob < 0.1:
            print("✓ Model correctly detected silence")
        else:
            print("⚠ Warning: Model detected speech in silence (may be OK)")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        return False


def test_vad_service():
    """Test that the VAD service can be imported."""
    print("\nTesting VAD service import...")
    
    try:
        sys.path.insert(0, '/Users/arik/Documents/GitHub/JustNoise/pi-aggregator')
        from vad import SileroVAD
        
        print("✓ VAD service imports successfully")
        
        # Try to instantiate
        vad = SileroVAD(sample_rate=16000, device='cpu')
        print("✓ SileroVAD instance created")
        
        # Test processing a chunk (512 samples for 16kHz)
        import numpy as np
        chunk = np.zeros(512, dtype=np.int16)  # 32ms at 16kHz (required size)
        result = vad.process_chunk(chunk)
        
        print(f"✓ Chunk processing works (result: {result})")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to test VAD service: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("Silero VAD Installation Test")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: Imports
    if not test_imports():
        all_passed = False
        print("\n⚠ Install dependencies with: just setup-vad")
        return
    
    # Test 2: Model loading
    if not test_model_load():
        all_passed = False
    
    # Test 3: VAD service
    if not test_vad_service():
        all_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed! VAD is ready to use.")
        print("\nNext steps:")
        print("  1. Record audio: just record test.wav")
        print("  2. Test VAD: just vad-test test.wav")
        print("  3. Live VAD: just vad-live")
    else:
        print("❌ Some tests failed. See errors above.")
    print("=" * 60)


if __name__ == '__main__':
    main()
