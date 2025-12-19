"""EPR server deployment configuration."""

from dataclasses import dataclass


@dataclass
class EPRConfig:
    host: str
    user: str
    deploy_path: str
    ssh_key_path: str = "~/.ssh/epr_deploy_key"


ENVIRONMENTS = {
    "i01": EPRConfig(
        host="10.80.1.201",
        user="socci",
        deploy_path="/opt/sva-soc-epr/packages",
    ),
    "p01": EPRConfig(
        host="10.80.1.233",
        user="socci",
        deploy_path="/opt/sva-soc-epr/packages",
    ),
}


def get_config(env: str) -> EPRConfig:
    """Get configuration for the specified environment."""
    if env not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment: {env}. Valid: {list(ENVIRONMENTS.keys())}")
    return ENVIRONMENTS[env]
