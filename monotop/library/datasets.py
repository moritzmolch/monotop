import glob
import logging
import os
import re
from typing import List, Optional
import yaml


class Dataset():

    logger = logging.getLogger("Dataset")

    dump_keys = {
        "name",
        "key",
        "filelist",
        "cross_section",
        "is_data",
        "is_mc",
    }

    def __init__(
        self,
        name: str,
        key: Optional[str] = None,
        filelist: Optional[List[str]] = None,
        cross_section: Optional[float] = None,
        is_data: Optional[bool] = None,
        is_mc: Optional[bool] = None,
    ):
       self._name = name
       self._key = key or ""
       self._filelist = filelist or []
       self._cross_section = cross_section or 1.0
       
       self._is_data = is_data if is_data is not None else False
       self._is_mc = is_mc if is_mc is not None else False

       self.logger.info("created dataset '{}'".format(self._name))

    @property
    def name(self):
        return self._name

    @property
    def filelist(self):
        return self._filelist

    @property
    def key(self):
        return self._key

    @property
    def cross_section(self):
        return self._cross_section

    @property
    def is_data(self):
        return self._is_data

    @property
    def is_mc(self):
        return self._is_mc

    def dump(self, file_path: os.PathLike):
        self.logger.info("dump information of dataset '{}' in file '{}'".format(self.name, file_path))
        with open(file_path, mode="w") as f:
            yaml.safe_dump({k: getattr(self, k) for k in self.dump_keys}, f)

    def compile_filelist(self):
        self.logger.info("compile filelist of dataset '{}' with key '{}'".format(self.name, self.key))

        # divide the DAS key into its parts
        key_parts = self.key.split("/")

        # if no valid key is given, filelist cannot be compiled
        if len(key_parts) < 2:
            raise RuntimeError("dataset '{}' does not have a DAS key".format(self.name))

        # get the dataset name (full part between the first two slashes)
        dataset_name = key_parts[1]

        # evaluate the part between the second and the third slash, which gives the production tag and the user
        m = re.match("^((\w+)-(KITv\d_CustomNanoV9(_|-)((MC)|(Data))_([\w\d]+)))-([\w\d]+)$", key_parts[2])
        if m is None:
            raise RuntimeError("DAS key of dataset '{}' does not follow expected pattern".format(self.name))
        user = m.group(2)
        production_tag = m.group(3)

        base_path = os.path.join(
            "/pnfs/desy.de/cms/tier2/store/user",
            user,
            "customNano",
            dataset_name,
            production_tag,
        )

        self.logger.info("search for dataset files in '{}'".format(base_path))

        # from here on, let glob do the rest of the work
        filelist = list(
            glob.glob(
                os.path.join(
                    base_path,
                    "*",
                    "*",
                    "*.root",
                )
            )
        )

        self.logger.info("found {} files".format(len(filelist)))

        self._filelist = filelist

        return filelist


class DatasetGroup():

    logger = logging.getLogger("DatasetGroup")

    def __init__(
        self,
        name: str,
        datasets: Optional[List[Dataset]] = None,
    ):
        self._name = name
        self._datasets = datasets or []

    @property
    def name(self):
        return self._name
    
    @property
    def datasets(self):
        return self._datasets

    def add_dataset(self, *args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], Dataset):
            dataset = args.pop(0)
            self._add_dataset_object(dataset)
        else:
            self._add_dataset_object(Dataset(*args, **kwargs))

    def _add_dataset_object(self, dataset: Dataset):
        if dataset.name in [dataset.name for dataset in self._datasets]:
            raise ValueError(
                "dataset with name '{}' already exists in dataset group '{}'".format(
                    dataset.name,
                    self.name,
                )
            )
        self._datasets.append(dataset)

    def dump(self, parent_dir_path: os.PathLike):
        base_dir_path = os.path.join(parent_dir_path, self.name)
        self.logger.info("dump information of dataset group '{}' in directory '{}'".format(self.name, base_dir_path))
        if not os.path.exists(base_dir_path):
            os.makedirs(base_dir_path)
        for dataset in self.datasets:
            dataset.dump(os.path.join(base_dir_path, "{}.yaml".format(dataset.name)))

