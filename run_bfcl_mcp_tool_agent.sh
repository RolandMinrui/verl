set -x

ulimit -n 65535

export VLLM_USE_V1=1
export HF_HUB_OFFLINE=1 # disable hf when offline

PROJECT_DIR="$(pwd)"
CONFIG_PATH="$PROJECT_DIR/tools/configs"
CONFIG_NAME="bfcl_multiturn_grpo"
TIMESTAMP="$(date +"%Y%m%d-%H%M")"
EXP_NAME="qwen3-1.7b-bfcl-n16-vllm-think"

python3 -m verl.trainer.main_ppo \
    --config-path="$CONFIG_PATH" \
    --config-name="$CONFIG_NAME" \
    algorithm.adv_estimator=gdpo \
    data.train_batch_size=1 \
    data.max_prompt_length=2048 \
    data.max_response_length=1024 \
    data.filter_overlong_prompts=False \
    data.apply_chat_template_kwargs.enable_thinking=True \
    actor_rollout_ref.model.path=Qwen/Qwen3-1.7B \
    actor_rollout_ref.actor.optim.lr=1e-6 \
    actor_rollout_ref.model.use_remove_padding=True \
    actor_rollout_ref.actor.ppo_mini_batch_size=1 \
    actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=1 \
    actor_rollout_ref.actor.use_kl_loss=True \
    actor_rollout_ref.actor.kl_loss_coef=0.001 \
    actor_rollout_ref.actor.kl_loss_type=low_var_kl \
    actor_rollout_ref.actor.entropy_coeff=0 \
    actor_rollout_ref.model.enable_gradient_checkpointing=True \
    actor_rollout_ref.actor.fsdp_config.param_offload=False \
    actor_rollout_ref.actor.fsdp_config.optimizer_offload=False \
    actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu=1 \
    actor_rollout_ref.rollout.tensor_model_parallel_size=1 \
    actor_rollout_ref.rollout.name=vllm \
    actor_rollout_ref.rollout.mode=async \
    actor_rollout_ref.rollout.gpu_memory_utilization=0.75 \
    actor_rollout_ref.rollout.n=8 \
    actor_rollout_ref.ref.log_prob_micro_batch_size_per_gpu=1 \
    actor_rollout_ref.ref.fsdp_config.param_offload=True \
    actor_rollout_ref.rollout.trace.backend=tensorboard \
    actor_rollout_ref.rollout.trace.token2text=True \
    algorithm.use_kl_in_reward=False \
    trainer.critic_warmup=0 \
    trainer.logger='["console","tensorboard"]' \
    trainer.project_name='bfcl_tool-agent' \
    trainer.experiment_name="${EXP_NAME}-${TIMESTAMP}" \
    trainer.n_gpus_per_node=1 \
    trainer.nnodes=1 \
    trainer.save_freq=-1 \
    trainer.test_freq=1 \
    data.log_dump_path=$PROJECT_DIR/log/$EXP_NAME/$TIMESTAMP.jsonl \
    data.train_files=$PROJECT_DIR/data/BFCL/multi-turn/train.parquet \
    data.val_files=$PROJECT_DIR/data/BFCL/multi-turn/test.parquet \
    actor_rollout_ref.rollout.multi_turn.tool_config_path=$PROJECT_DIR/tools/mcp_configs/bfcl_mcp_server.json \
    trainer.total_epochs=1 $@ \
    custom_reward_function.path=$PROJECT_DIR/recipe/tool_agent/tool_agent_rule_based.py\
    custom_reward_function.name=compute_score \