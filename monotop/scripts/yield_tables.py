import argparse
from collections import OrderedDict
from itertools import product
import numpy as np
import re
import ROOT
import os
import json
import pandas as pd
from pandas.io.formats.style import Styler
import subprocess

from monotop.constants import STORE_PATH


# the default combine input file
DEFAULT_COMBINE_FILE = "/nfs/dust/cms/user/mwassmer/MonoTop/NanoAOD/Fit/monotop-datacards-v2/combined_cards/v29_hadronic/all_years/Mphi_1000_Mchi_150/fits/fitDiagnosticsdatacard_hadronic_all_years_Mphi_1000_Mchi_150_bkg_asimov_toy_postfituncs.root"

# the pattern of the keys for accessing individual bins
BIN_KEY_PATTERN = re.compile(r"^YEAR_(\d+((preVFP)|(postVFP))?)_((PASS)|(FAIL))_(\w)_((dycr_)|(wcr_)|(ttcr_))?(.+)_((pass)|(fail))_bin_(\d+)$")

# category names (in keys) and labels (in the final table)
CATEGORY_LABELS = OrderedDict([
    ("SR", "SR"),
    ("CR_Z_ElEl", "Z($\\mathrm{{e}}\\bar{{\\mathrm{{e}}}}$) CR"),
    ("CR_Z_MuMu", "Z($\\mu\\bar{{\\mu}}$) CR"),
    ("CR_W_electron", "W (e) CR"),
    ("CR_W_muon", "W ($\\mu$) CR"),
    ("CR_TT_electron", "$\\mathrm{{t}}\\bar{{\\mathrm{{t}}}}$ (e) CR"),
    ("CR_TT_muon", "$\\mathrm{{t}}\\bar{{\\mathrm{{t}}}}$ ($\\mu$) CR"),
    ("CR_Gamma", "$\\gamma$ CR"),
])

# process names (in keys) and labels (in the final table)
PROCESS_LABELS = OrderedDict([
    ("data", "data"),
    ("total", "total background"),
    ("DYJetsToLL", "Z($\\ell\\ell$)+jets"),
    ("ZJetsToNuNu", "Z($\\nu\\nu$)+jets"),
    ("WJetsToLNu_stitched", "W($\\ell\\nu$)+jets"),
    ("G1Jet_Ptbinned", "$\\gamma$+jets"),
    ("ttbar", "$\\mathrm{{t}}\\bar{{\\mathrm{{t}}}}$"),
    ("SingleTop", "single top"),
    ("diboson", "diboson"),
    ("qcd", "QCD"),
])


def create_bin_groups(bin_names):
    bin_groups = {}

    # get information for constructing multi-index columns, which are characterized by a three-tuple (era, top tagger region, category)
    for bin_name in bin_names:

        # get information from the bin name by parsing it with a regular expression
        m = BIN_KEY_PATTERN.match(bin_name)
        era = m.group(1)
        category = m.group(13)
        top_tagger_pass_or_fail = m.group(5).lower()

        # add bin name to one of the bin groups for a category
        # each category is characterized by the data-taking era, the top tagger pass or fail region and the category name itself
        multi_index_key = (era, top_tagger_pass_or_fail, category)
        bin_groups.setdefault(multi_index_key, []).append(bin_name)

    return bin_groups


def create_yield_data_frame(bin_groups, yields_combine):
    # get the column names, which are the bin group keys
    columns = pd.MultiIndex.from_tuples(
        bin_groups.keys(), names=["era", "top_tagger_region", "category"]
    )

    # collect all processes that appear in the bins
    processes = set()
    for bin_names in bin_groups.values():
        for bin_name in bin_names:
            for key in yields_combine.Get(bin_name).GetListOfKeys():
                process = key.GetName()
                if process in ["total_background", "total_signal", "total_covar", "Mphi_1000_Mchi_150"]:
                    continue
                processes.add(process)
    index = pd.MultiIndex.from_product([processes, ["yield", "variance_down", "variance_up", "string"]], names=["process", "yield_variance"])

    # construct and return the data frame
    return pd.DataFrame(np.zeros((len(index), len(columns)), dtype=np.float64), index=index, columns=columns)


def get_total_correlated_variance(bin_group_names, total_cov_combine):

    # get the ROOT histogram indices corresponding to the bin names
    index_hist = []
    for bin_name in bin_group_names:
        index_hist.append(total_cov_combine.GetXaxis().FindBin(bin_name + "_0"))

    # calculate the sum of the covariance matrix elements, which is the variance of the total yield
    total_variance = 0
    for i, j in product(index_hist, index_hist):
        total_variance += total_cov_combine.GetBinContent(i, j)

    return total_variance


def fill_category_values(yields, category_key, bin_group_names, yields_combine, total_cov_combine):

    for bin_name in bin_group_names:

        # get the results for the current bin
        yields_combine_bin = yields_combine.Get(bin_name)

        for key in yields_combine_bin.GetListOfKeys():
            process = key.GetName()

            # ignore entries that we are not interested in
            if process in ["total_background", "total_signal", "total_covar", "Mphi_1000_Mchi_150"]:
                continue

            elif process == "data":
                if category_key[1] == "pass" and category_key[2] == "SR":
                    # do not write out anything in the signal region
                    yields.loc[(process, "yield"), category_key] = -1
                    yields.loc[(process, "variance_down"), category_key] += 10000
                    yields.loc[(process, "variance_up"), category_key] += 10000

                else:
                    # add yield and variances of this process in this bin to the data frame
                    yields.loc[(process, "yield"), category_key] += yields_combine_bin.Get(process).GetPointY(0)
                    yields.loc[(process, "variance_down"), category_key] += np.power(yields_combine_bin.Get(process).GetErrorYlow(0), 2)
                    yields.loc[(process, "variance_up"), category_key] += np.power(yields_combine_bin.Get(process).GetErrorYhigh(0), 2)

            else:
                # add yield of this process in this bin to the data frame
                yields.loc[(process, "yield"), category_key] += yields_combine_bin.Get(process).GetBinContent(1)

                # if this is not the total yield, the variances are added up
                if process != "total":
                    yields.loc[(process, "variance_down"), category_key] += np.power(yields_combine_bin.Get(process).GetBinError(1), 2)
                    yields.loc[(process, "variance_up"), category_key] += np.power(yields_combine_bin.Get(process).GetBinError(1), 2)

    # for the total yield, the correlated uncertainty/variance is calculated
    yields.loc[("total", "variance_down"), category_key] = get_total_correlated_variance(bin_group_names, total_cov_combine)
    yields.loc[("total", "variance_up"), category_key] = get_total_correlated_variance(bin_group_names, total_cov_combine)

    for process in np.unique(yields.index.get_level_values(0)):
        yield_val = np.array(np.round(yields.loc[(process, "yield"), category_key], decimals=0), dtype=np.int64)
        sigma_down_val = np.array(np.round(np.sqrt(yields.loc[(process, "variance_down"), category_key]), decimals=0), dtype=np.int64)
        sigma_up_val = np.array(np.round(np.sqrt(yields.loc[(process, "variance_up"), category_key]), decimals=0), dtype=np.int64)

        if process == "data" and category_key[1] == "pass" and category_key[2] == "SR":
            yields.loc[(process, "string"), category_key] = "{\\bfseries{}blind}"

        else:
            if sigma_down_val == sigma_up_val:
                yields.loc[(process, "string"), category_key] = "${} \\pm {}$".format(yield_val, sigma_down_val)
            else:
                yields.loc[(process, "string"), category_key] = "${{{}}}_{{-{}}}^{{+{}}}$".format(yield_val, sigma_down_val, sigma_up_val)

    return yields


def construct_yield_table(yields, era, top_tagger_pass_or_fail, category_labels, process_labels):

        # get the relevant sub-table
        row_mask = yields.index.get_loc_level(["string"], level=["yield_variance"])
        column_mask = yields.columns.get_loc_level([era, top_tagger_pass_or_fail], level=["era", "top_tagger_region"])
        yield_table = yields.iloc[row_mask[0], column_mask[0]].copy()
        yield_table.index = yield_table.index.droplevel(level="yield_variance")
        yield_table.columns = yield_table.columns.droplevel(level=["era", "top_tagger_region"])

        yield_table = yield_table.loc[process_labels.keys(), category_labels.keys()]
        yield_table.index = pd.Index([process_labels[k] for k in yield_table.index])
        yield_table.columns = pd.Index(category_labels[k] for k in yield_table.columns)

        yield_table.style.set_properties(
            scriptsize="--latex--rwrap",
        )

        table_string = yield_table.style.to_latex(
            caption="{}, top tagger {}".format(era, top_tagger_pass_or_fail),
            column_format="l" + len(yield_table.columns) * "c",
            hrules=True,
        )
        
        # decrease fontsize
        table_string = table_string.replace("\\begin{table}", "\\begin{table}\n\\centering\\scriptsize")

        # remove booktabs commands
        table_string = table_string.replace("\\toprule", "\\hline").replace("\\midrule", "\\hline").replace("\\bottomrule", "\\hline")

        # add additional horizontal bars after data and background
        table_string_rows = table_string.split("\n")
        index_data = table_string_rows.index([row for row in table_string_rows if row.strip().startswith("data")][0])
        index_bkg = table_string_rows.index([row for row in table_string_rows if row.strip().startswith("total background")][0])
        table_string_rows = table_string_rows[0:(index_data + 1)] + ["\\hline"] + table_string_rows[(index_data + 1):(index_bkg + 1)] + ["\\hline"] + table_string_rows[(index_bkg + 1)::]

        # concatenate the whole string again
        table_string = "\n".join(table_string_rows)

        return table_string


if __name__ == "__main__":


    # create the argument parser
    parser = argparse.ArgumentParser(description="Creating post-fit yield tables for the CMS Monotop analysis")
    parser.add_argument(
        "--combine-file",
        help="path to the file that contains the results of the combine fit",
        required=True,
    )
    parser.add_argument(
        "--output-path",
        help="path to the output directory; default: {}".format(os.path.join(STORE_PATH, "yields")),
        default=os.path.join(STORE_PATH, "yields"),
    )
    arguments = parser.parse_args()

    # parse the input file
    combine_file_path = os.path.abspath(arguments.combine_file)

    output_dir = destination = os.path.join(STORE_PATH, "yields", os.path.splitext(os.path.basename(combine_file_path))[0])
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        # load the ROOT file
        root_file = ROOT.TFile.Open(combine_file_path, "READ")

        # get the postfit yields and covariances from the ROOT file
        yields_combine = root_file.Get("shapes_fit_b")
        total_cov_combine = yields_combine.Get("overall_total_covar")

        # construct list of bin names that match the expected pattern
        bin_names = [k.GetName() for k in yields_combine.GetListOfKeys() if BIN_KEY_PATTERN.match(k.GetName())]

        # group bins w.r.t. era, top tagger region and category
        bin_groups = create_bin_groups(bin_names)

        # create data frame that contains the final results for the yields and uncertainties
        yields = create_yield_data_frame(bin_groups, yields_combine)

        # fill the yield table with values
        for category_key, bin_group_names in bin_groups.items():
            yields = fill_category_values(yields, category_key, bin_group_names, yields_combine, total_cov_combine)

        # dump the results into a JSON file
        destination = os.path.join(output_dir, "yield_table_results.h5")
        yields.to_hdf(destination, key="yields")

        # construct the yield tables and dump them into LaTeX files
        for era in np.unique(yields.columns.get_level_values(level="era")):
            for top_tagger_pass_or_fail in np.unique(yields.columns.get_level_values(level="top_tagger_region")):

                # produce a latex file with the table
                yield_table = construct_yield_table(yields, era, top_tagger_pass_or_fail, CATEGORY_LABELS, PROCESS_LABELS)
                prefix = "\n".join([
                    r"\documentclass[11pt,a4paper]{article}",
                    r"\usepackage[T1]{fontenc}",
                    r"\usepackage[utf8]{inputenc}",
                    r"\usepackage[left=2.0cm, right=2.0cm]{geometry}"
                    r"\usepackage{amsmath}",
                    r"\usepackage{amssymb}",
                    r"\usepackage{amsfonts}",
                    r"\usepackage{booktabs}",
                    r"",
                    r"\begin{document}"
                    r"",
                    r"",
                ])
                suffix = "\n".join([
                    r"",
                    r"",
                    r"\end{document}"
                ])
                destination = os.path.join(output_dir, "yield_table_{}_{}.tex".format(era, top_tagger_pass_or_fail))
                destination_raw = os.path.join(output_dir, "yield_table_raw_{}_{}.tex".format(era, top_tagger_pass_or_fail))
                with open(destination, mode="w") as f:
                    f.write(prefix + yield_table + suffix)
                with open(destination_raw, mode="w") as f:
                    f.write(yield_table)

                # compile the PDF
                p = subprocess.Popen(["/usr/bin/pdflatex", os.path.basename(destination)], cwd=output_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
                out, err = p.communicate()

                if p.returncode != 0:
                    raise Exception("LaTeX compilation of '{}' failed\noutput: {}\nerror: {}".format(destination, out.decode("utf-8"), err.decode("utf-8")))

    except Exception:
        raise

    finally:
        # close the ROOT file safely
        root_file.Close()



