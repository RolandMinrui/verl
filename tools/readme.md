### Envrionment Setup
```
conda create -n verl python==3.11
conda activate verl

git clone https://github.com/RolandMinrui/verl
cd verl

bash scripts/install_vllm_sglang_mcore.sh # If you need to run with megatron
USE_MEGATRON=0 bash scripts/install_vllm_sglang_mcore.sh # Or if you simply need to run with FSDP

pip install -e .

pip install fastmcp jsonlines toml

pip install arxiv ddgs semanticscholar wikipedia-api # For search envs
```

### Environment Structure
```
envs/
├── agent_loop/
├── configs/
├── database/
├── manager/
├── reward/
├── tools/
└── utils/
```