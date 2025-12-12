"""EPR server deployment configuration."""

from dataclasses import dataclass


@dataclass
class EPRConfig:
    host: str
    user: str
    deploy_path: str
    ssh_key_path: str = "~/.ssh/epr_deploy_key"


ENVIRONMENTS = {
    "staging": EPRConfig(
        host="10.10.145.90",
        user="socci",
        deploy_path="/opt/sva-soc-epr/packages",
    ),
    "production": EPRConfig(
        host="10.10.146.103",
        user="socci",
        deploy_path="/opt/sva-soc-epr/packages",
    ),
}


def get_config(env: str) -> EPRConfig:
    """Get configuration for the specified environment."""
    if env not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment: {env}. Valid: {list(ENVIRONMENTS.keys())}")
    return ENVIRONMENTS[env]
