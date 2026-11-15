# Fixed first-party bridge. Numeric CSV only; never evaluate input R expressions.
args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 2, as.character(getRversion()) == "4.2.2")
service <- args[[1]]
folder <- args[[2]]
data <- read.csv("input.csv", check.names = FALSE)
options(digits = 17, warn = 2)
if (service == "pricesensitivitymeter") {
  files <- c("psm_weighted_functions.R", "psm_class_summary.R", "psm_data_processing.R",
             "psm_validation.R", "psm-utils.R", "psm_utils.R", "psm_plot.R",
             "psm_constants.R", "psm_functions.R")
  for (name in files) source(file.path(folder, name), local = TRUE)
  r <- psm_analysis(data$toocheap, data$cheap, data$expensive, data$tooexpensive,
                    validate = TRUE, interpolate = FALSE,
                    intersection_method = "min", acceptable_range = "original")
  stopifnot(!r$weighted, !r$nms)
  output <- data.frame(sample = r$total_sample, invalid = r$invalid_cases,
                       lower = r$pricerange_lower, upper = r$pricerange_upper,
                       idp = r$idp, opp = r$opp)
} else if (service == "robyn") {
  source(file.path(folder, "transformation.R"), local = TRUE)
  carry <- adstock_geometric(data$spend, theta = data$theta[[1]])$x_decayed
  saturated <- saturation_hill(carry, alpha = data$alpha[[1]], gamma = data$gamma[[1]])
  output <- data.frame(adstock = carry, saturation = saturated)
} else stop("Unsupported operation")
write.table(output, file = "output.csv", sep = ",", row.names = FALSE, col.names = TRUE)
