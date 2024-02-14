import os
import re
import yaml

from ..lib.datasets import DatasetGroup
from ..constants import CONFIG_PATH


def load_dataset_groups(cfg_file_path: os.PathLike):
    with open(cfg_file_path, mode="r") as f:
        cfg = yaml.safe_load(f)

    dataset_groups = []

    for group_name, datasets in cfg.values():
        dataset_group = DatasetGroup(name=group_name)
        for dataset in datasets:
            dataset_group.add_dataset(
                name=dataset["name"],
                das_key=dataset["das"]["key"],
                cross_section=dataset["das"]["cross_section"],
                is_data=dataset.get("is_data", False),
                is_mc=dataset.get("is_mc", False),
            )
        dataset_groups.append(dataset_group)

    return dataset_groups



if __name__ == "__main__":
    dataset_groups = load_dataset_groups(os.path.join(CONFIG_PATH, "CustomNanoAODv9_Data_2018.yaml"))
    dataset_groups.update(load_dataset_groups(os.path.join(CONFIG_PATH, "CustomNanoAODv9_MC_2018.yaml")))

    for dataset_group in dataset_groups:
        for dataset in dataset_group.datasets:
            print("compiling filelist for dataset {}".format(dataset.name))
            _ = dataset.compile_filelist()

    dataset_group.dump(os.path.join(CONFIG_PATH, "datasets"))
