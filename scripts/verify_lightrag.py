"""
LightRAG Installation Verification Script
Tests that LightRAG is properly installed and configured
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def verify_lightrag():
    """Verify LightRAG installation and basic functionality"""
    print("=" * 60)
    print("LightRAG Installation Verification")
    print("=" * 60)

    # Test 1: Import lightrag
    print("\n[1/5] Testing LightRAG import...")
    try:
        from lightrag import LightRAG, QueryParam
        from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
        from lightrag.kg.shared_storage import initialize_pipeline_status
        print("✅ LightRAG imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import LightRAG: {e}")
        return False

    # Test 2: Import networkx
    print("\n[2/5] Testing NetworkX import...")
    try:
        import networkx as nx
        print(f"✅ NetworkX imported successfully (version: {nx.__version__})")
    except ImportError as e:
        print(f"❌ Failed to import NetworkX: {e}")
        return False

    # Test 3: Import Mnemosyne service
    print("\n[3/5] Testing Mnemosyne LightRAG service...")
    try:
        from backend.services.lightrag_service import (
            LightRAGService,
            get_lightrag_service
        )
        print("✅ LightRAG service imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import LightRAG service: {e}")
        return False

    # Test 4: Configuration
    print("\n[4/5] Testing configuration...")
    try:
        from backend.config import settings
        assert hasattr(settings, "LIGHTRAG_ENABLED")
        assert hasattr(settings, "LIGHTRAG_WORKING_DIR")
        assert hasattr(settings, "LIGHTRAG_TOP_K")
        print(f"✅ Configuration loaded successfully")
        print(f"   - LIGHTRAG_ENABLED: {settings.LIGHTRAG_ENABLED}")
        print(f"   - LIGHTRAG_WORKING_DIR: {settings.LIGHTRAG_WORKING_DIR}")
        print(f"   - LIGHTRAG_TOP_K: {settings.LIGHTRAG_TOP_K}")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

    # Test 5: Service initialization (requires OpenAI key)
    print("\n[5/5] Testing service initialization...")
    try:
        service = get_lightrag_service()
        print(f"✅ Service created (enabled: {service.enabled})")

        if service.enabled and settings.OPENAI_API_KEY:
            print("   Attempting to initialize service...")
            await service.initialize()
            print(f"✅ Service initialized successfully")
            await service.cleanup()
            print(f"✅ Service cleaned up successfully")
        else:
            if not settings.OPENAI_API_KEY:
                print("   ⚠️  Skipping initialization (OPENAI_API_KEY not set)")
            else:
                print("   ⚠️  Service is disabled in configuration")

    except Exception as e:
        print(f"❌ Service initialization error: {e}")
        return False

    # Summary
    print("\n" + "=" * 60)
    print("✅ LightRAG verification completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Set OPENAI_API_KEY in .env file")
    print("2. Test document insertion and querying")
    print("3. Integrate with document processing pipeline")
    print()

    return True


if __name__ == "__main__":
    result = asyncio.run(verify_lightrag())
    sys.exit(0 if result else 1)
