import logging
import os
import re
import yaml

from monotop.library.datasets import DatasetGroup
from monotop.constants import BASE_PATH, CONFIG_PATH

logging.basicConfig(level=logging.INFO)


def load_dataset_groups(cfg_file_path: os.PathLike):
    with open(cfg_file_path, mode="r") as f:
        cfg = yaml.safe_load(f)

    dataset_groups = []

    for group_name, datasets in cfg.items():
        dataset_group = DatasetGroup(name=group_name)
        for dataset in datasets:
            dataset_group.add_dataset(
                name=dataset["name"],
                key=dataset.setdefault("das", {}).get("key", None),
                cross_section=dataset.get("cross_section", None),
                is_data=dataset.get("is_data", False),
                is_mc=dataset.get("is_mc", False),
            )
        dataset_groups.append(dataset_group)

    return dataset_groups


if __name__ == "__main__":

    dataset_groups = load_dataset_groups(os.path.join(CONFIG_PATH, "datasets_CustomNanoAODv9_Data_2018.yaml"))
    dataset_groups += load_dataset_groups(os.path.join(CONFIG_PATH, "datasets_CustomNanoAODv9_MC_2018.yaml"))

    for dataset_group in dataset_groups:
        for dataset in dataset_group.datasets:
            _ = dataset.compile_filelist()
        dataset_group.dump(os.path.join(BASE_PATH, "store", "datasets", "2018"))

