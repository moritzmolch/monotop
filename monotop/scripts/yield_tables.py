from itertools import product
import numpy as np
import re
import ROOT
import os
import json

from monotop.constants import STORE_PATH


#ROOT.gROOT.SetBatch(ROOT.kTRUE)

TEST_FILE = "/nfs/dust/cms/user/mwassmer/MonoTop/NanoAOD/Fit/monotop-datacards-v2/combined_cards/v29_hadronic/all_years/Mphi_1000_Mchi_150/fits/fitDiagnosticsdatacard_hadronic_all_years_Mphi_1000_Mchi_150_bkg_asimov_toy_postfituncs.root"
BIN_KEY_PATTERN = re.compile(r"^YEAR_(\d+((preVFP)|(postVFP))?)_((PASS)|(FAIL))_(\w)_(.+)_bin_(\d+)$")


f = ROOT.TFile.Open(TEST_FILE, "READ")

shapes_fit_b = f.Get("shapes_fit_b")


bin_names = [k.GetName() for k in shapes_fit_b.GetListOfKeys() if BIN_KEY_PATTERN.match(k.GetName())]


# get the yields and the variances for each individual bin
bkg_total_yield = np.zeros((len(bin_names), ), dtype=np.float64)
bkg_total_var = np.zeros((len(bin_names), ), dtype=np.float64)
data_yield = np.zeros((len(bin_names), ), dtype=np.float64)
data_var_down = np.zeros((len(bin_names), ), dtype=np.float64)
data_var_up = np.zeros((len(bin_names), ), dtype=np.float64)

process_yields = {}
process_variances = {}


for i, name in enumerate(bin_names):
    yields_bin = shapes_fit_b.Get(name)
    bkg_total_yield[i] = yields_bin.Get("total").GetBinContent(1)
    bkg_total_var[i] = yields_bin.Get("total_covar").GetBinContent(1)
    data_yield[i] = yields_bin.Get("data").GetPointY(0)
    data_var_down[i] = np.power(yields_bin.Get("data").GetErrorYlow(0), 2)
    data_var_up[i] = np.power(yields_bin.Get("data").GetErrorYhigh(0), 2)

    # get yields and variances for individual processes
    for k in yields_bin.GetListOfKeys():

        # exclude total yields and covariances
        process_name = k.GetName()
        if process_name in ["total", "total_background", "total_covar", "data"]:
            continue

        # create the dictionaries for the processes if they do not exist yet
        process_yields.setdefault(process_name, np.zeros(len(bin_names), dtype=np.float64))
        process_variances.setdefault(process_name, np.zeros(len(bin_names), dtype=np.float64))

        # get the histogram for the process
        yields_process_bin = yields_bin.Get(process_name)

        # fill the process yield and variance arrays
        process_yields[process_name][i] = yields_process_bin.GetBinContent(1)
        process_variances[process_name][i] = np.power(yields_process_bin.GetBinError(1), 2)

# remove lists for signal processes
process_yields.pop("Mphi_1000_Mchi_150")
process_variances.pop("total_signal")

# get the covariance matrix
overall_total_covar = shapes_fit_b.Get("overall_total_covar")
bkg_total_covmat = np.zeros((len(bin_names), len(bin_names)), dtype=np.float64)
for i, j in product(range(len(bin_names)), range(len(bin_names))):
    bin_name_i = bin_names[i]
    bin_name_j = bin_names[j]
    i_hist = overall_total_covar.GetXaxis().FindBin(bin_name_i + "_0")
    j_hist = overall_total_covar.GetYaxis().FindBin(bin_name_j + "_0")
    bkg_total_covmat[i, j] = overall_total_covar.GetBinContent(i_hist, j_hist)

# close the ROOT file
f.Close()


categories = {}

# categorize the bins
for bin_name in bin_names:
    m = BIN_KEY_PATTERN.match(bin_name)
    era = m.group(1)
    category = m.group(9)
    top_tagger_pass_or_fail = m.group(5).lower().lower()
    bin_index = int(m.group(10))

    # add a dictionary for each era
    categories.setdefault(era, {})

    # add a sub-dictionary for each category
    categories[era].setdefault(category, {})
    
    # add sub-dictionary for top tagger pass and fail regions
    categories[era][category].setdefault(top_tagger_pass_or_fail, {})

    # add the bin name and the bin indices
    categories[era][category][top_tagger_pass_or_fail].setdefault("bin_names", []).append(bin_name)


for era, categories_era in categories.items():

    for category_name, category in categories_era.items():

        for top_tagger_fail_or_pass, top_tagger_category in category.items():

            # get the bin indices in the global yield vector/covariance matrix
            bin_index = []
            for name in top_tagger_category["bin_names"]:
                bin_index.append(bin_names.index(name))
            bin_index = np.array(bin_index, dtype=np.int64)

            # calculate the total yield and variance (taking correlations into account) in the category
            yield_category = np.sum(bkg_total_yield[bin_index])

            # sum up yields of individual processes and calculate sum of variances

            yield_process = {k: 0 for k in process_yields.keys()}
            variance_process = {k: 0 for k in process_variances.keys()}
            for i in bin_index:
                for k in process_yields:
                    yield_process[k] += process_yields[k][i]
                    variance_process[k] += process_variances[k][i]

            # calculate index combination of sub-matrix of covariance matrix needed for this category
            bin_index_i, bin_index_j = zip(*product(bin_index, bin_index))
            bin_index_i, bin_index_j = np.array(bin_index_i), np.array(bin_index_j)

            variance_category = np.sum(bkg_total_covmat[bin_index_i, bin_index_j])

            top_tagger_category.update({
                "yield_category": yield_category,
                "variance_category": variance_category,
                "yield_process": yield_process,
                "variance_process": variance_process,
            })
    

dest_path = os.path.join(STORE_PATH, "yield_tables", "yields.json")
if not os.path.exists(os.path.dirname(dest_path)):
    os.makedirs(os.path.dirname(dest_path))

with open(dest_path, mode="w") as f:
    json.dump(categories, f)
