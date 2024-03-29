import functools
import pathlib
import yaml

from pydantic import BaseModel, SecretStr


class RabbitMQConfig(BaseModel):
    host: str
    username: str
    password: SecretStr
    vhost: str


class AppConfig(BaseModel):
    rmq: RabbitMQConfig

    project_dir: pathlib.Path
    static_dir: pathlib.Path


@functools.lru_cache
def get_config() -> AppConfig:
    path_to_config = pathlib.Path(__file__).parent.parent.resolve() / 'config.yml'
    assert path_to_config.exists(), 'No Config file!'

    project_dir = pathlib.Path(__file__).parent.parent.resolve()
    static_dir = pathlib.Path(__file__).parent.parent.joinpath('static').resolve()

    with path_to_config.open('r') as fp:
        config = yaml.safe_load(fp)
        config['project_dir'] = project_dir
        config['static_dir'] = static_dir
        return AppConfig.parse_obj(config)
