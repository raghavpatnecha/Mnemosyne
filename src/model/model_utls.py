from sentence_transformers import SentenceTransformer
import torch

def instantiate_model():
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    # check device being run on
    if device != 'cuda':
        print("==========\n"+
            "WARNING: You are not running on GPU so this may be slow.\n"+
            "If on Google Colab, go to top menu > Runtime > Change "+
            "runtime type > Hardware accelerator > 'GPU' and rerun "+
            "the notebook.\n==========")

    dense_model = SentenceTransformer(
        'msmarco-bert-base-dot-v5',
        device=device
    )
    return dense_model