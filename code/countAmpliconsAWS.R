
tic <- Sys.time()
message("Loading Libraries")

suppressMessages(library(argparser))
p <- arg_parser("utility to count amplicons for SwabSeq")
p <- add_argument(p, "--rundir",  default = ".", help="path to run")
p <- add_argument(p, "--basespaceID",  default = NA, help = "BaseSpace Run ID")
p <- add_argument(p, "--threads", default = 1, help = "number of threads for bcl2fastq & amatch")
p <- add_argument(p, "--debug", default = FALSE, type = "logical", help = "debug mode generates extra data and plots")
p <- add_argument(p, "--season", default = "winter", help = "we have 4 fwd/rev primer pair modes, each 
                  named after one of the 4 seasons. The original pairing is named winter and is the default.")
p <- add_argument(p, "--skipDownload", default = FALSE, type = "logical", help = "Skips basespace download.
                  If present, script expects bcl files to be present in rundir.")
args <- parse_args(p)

#load required packages
suppressMessages(library(tidyverse))
suppressMessages(library(Rqc))
suppressMessages(library(savR))
suppressMessages(library(Biostrings))
suppressMessages(library(xml2))


rundir <- args$rundir
basespaceID <- args$basespaceID
threads <- args$threads
debug <- args$debug
season <- args$season
skipDownload <- args$skipDownload


# setwd(rundir)
if (file.exists(rundir)){
  setwd(file.path(rundir))
} else {
  dir.create(file.path(rundir))
  setwd(file.path(rundir))
  
}


#-----------------------------------------------------------------------------------------------------

# If fastqs don't exist grab them from basespace
fastqR1  <- 'out/Undetermined_S0_R1_001.fastq.gz'

if(!file.exists(fastqR1)) {
  # Pull BCLs from basespace [skip this section if you already placed bcls in rundir/bcls/] ------------
  if(!skipDownload) {
    system(paste("bs download run --name", basespaceID, "-o ."))
  }
  
  # Run bcl2fastq to generate fastq.gz files (no demux is happening here)
  # NOTE: this is using 64 threads and running on a workstation, reduce threads if necessary
  system(paste("bcl2fastq --runfolder-dir . --output-dir out/ --create-fastq-for-index-reads  --ignore-missing-bcl --use-bases-mask=Y26,I10,I10 --processing-threads", threads, "--no-lane-splitting --sample-sheet /dev/null"))
}

rundir <- paste0(getwd(),"/")

# Align
system(paste0("python3 ../code/dict_align.py --rundir ./ --dictdir ../hash_tables/ --debug ", debug))


###################
# Reformat output #
###################
ss <- read_csv("../misc/SampleSheet_v2.csv")

results <- read_csv("results.csv") %>% 
  dplyr::rename(amplicon = amps,
                Count = `0`,
                index = i1,
                index2 = i2) %>% 
  mutate(mergedIndex = paste0(index, index2)) %>% 
  full_join(ss, by = c("mergedIndex","index","index2"))


# Add levels to indices for index swapping plots
ind1 <- ss %>% filter(season == !!season) %>% pull(index)
ind2 <- ss %>% filter(season == !!season) %>% pull(index2)

results <- results %>% 
  mutate(index = factor(index, levels = ind1),
         index2 = factor(index2, levels = ind2))

# Save results
write_csv(results, paste0(rundir, 'countTable.csv'))
saveRDS(results, file=paste0(rundir, 'countTable.RDS'),version=2)

##################
# Save QC Report #
##################

classification <- results %>%
  filter(season == !!season) %>% 
  #right_join(ss) %>% 
  group_by_at(names(.)[!names(.) %in% c("Count", "amplicon")]) %>% 
  summarise(S2_spike = sum(Count[grepl("S2_spike_0",amplicon)], na.rm = TRUE),
            S2 = sum(Count[amplicon == "S2"], na.rm = TRUE),
            RPP30 = sum(Count[amplicon == "RPP30"], na.rm = TRUE)) %>% 
  ungroup() %>% 
  mutate(S2_spike = ifelse(is.na(S2_spike), 0, S2_spike),
         S2 = ifelse(is.na(S2), 0, S2),
         RPP30 = ifelse(is.na(RPP30), 0, RPP30)) %>%
  group_by(Plate_ID) %>% 
  mutate(rp_ctrl_cutoff = quantile(RPP30[RPP30 >= 10], probs = 0.1, type = 8),
         rp_ctrl_cutoff = ifelse(is.na(rp_ctrl_cutoff), 0, rp_ctrl_cutoff)) %>% 
  ungroup() %>% 
  mutate(s2_vs_spike = ((S2 + 1) / (S2_spike + 1)),
         classification = ifelse(S2 + S2_spike < 100 & RPP30 < 10,
                                 "failed: low S2 & RPP30",
                                 ifelse(S2 + S2_spike < 100 & RPP30 >= 10,
                                        "failed: low S2",
                                        ifelse(S2 + S2_spike >= 100 & RPP30 < 10,
                                               "failed: low RPP30",
                                               ifelse(s2_vs_spike > 0.1 & RPP30 >= 10,
                                                      "COVID_pos",
                                                      ifelse(s2_vs_spike <= 0.1 & RPP30 >= 10,
                                                             "COVID_neg",
                                                             NA))))),
         ctrl_wells = ifelse(!Sample_Well %in% c("A01","B01"),
                             NA,
                             ifelse(Sample_Well == "A01" & RPP30 <= rp_ctrl_cutoff & S2_spike >= 100 & s2_vs_spike <= 0.1,
                                    "pass",
                                    ifelse(Sample_Well == "B01" & classification == "COVID_neg",
                                           "pass",
                                           "fail")))) %>% 
  arrange(Sample_ID)

write_csv(classification, "LIMS_results.csv")

amp.match.summary.df <- results %>% 
  group_by(amplicon) %>% 
  summarise(sum = sum(Count, na.rm = TRUE)) %>% 
  mutate(amplicon = ifelse(is.na(amplicon),
                           "no_align",
                           amplicon))

amp.match.summary <- amp.match.summary.df$sum
names(amp.match.summary) <- amp.match.summary.df$amplicon



sum_matched <- results %>% 
  filter(!is.na(Plate_ID),
         season == !!season) %>% 
  group_by(amplicon) %>% 
  summarise(num_matched = sum(Count, na.rm = TRUE)) %>% 
  mutate(amplicon = ifelse(is.na(amplicon),
                           "no_align",
                           amplicon)) %>% 
  left_join(amp.match.summary.df) %>% 
  dplyr::rename(num_reads = sum) %>% 
  dplyr::select(amplicon, num_reads, everything()) %>% 
  mutate(perc_match = paste0(round((num_matched / num_reads), 2) * 100, "%"),
         num_reads = format(num_reads, big.mark = ','),
         num_matched = format(num_matched, big.mark = ','))

sum_matched_df <- sum_matched %>% 
  dplyr::select(-amplicon) %>% 
  as.data.frame()
rownames(sum_matched_df) <- sum_matched$amplicon

# Run Info
rp <- read_xml("RunParameters.xml")

reagent <- xml_find_all(rp, '//ReagentKitRfidTag')
flow_cell <- xml_find_all(rp, '//FlowCellRfidTag')

run_info <- tibble(runID = xml_find_all(rp, '//RunID') %>% xml_text(),
       instrumentID = xml_find_all(rp, '//InstrumentID') %>% xml_text(),
       chemistry = xml_find_all(rp, '//Chemistry') %>% xml_text(),
       reagent_SerialNumber = xml_find_all(reagent, './/SerialNumber') %>% xml_text(),
       reagent_PartNumber = xml_find_all(reagent, './/PartNumber') %>% xml_text(),
       reagent_LotNumber = xml_find_all(reagent, './/LotNumber') %>% xml_text(),
       flowCell_SerialNumber = xml_find_all(flow_cell, './/SerialNumber') %>% xml_text(),
       flowCell_PartNumber = xml_find_all(flow_cell, './/PartNumber') %>% xml_text(),
       flowCell_LotNumber = xml_find_all(flow_cell, './/LotNumber') %>% xml_text()) %>% 
  pivot_longer(cols = 1:ncol(.))

write_csv(run_info, 'run_info.csv')

# Illumina stats
sav <- savR(rundir)
tMet <- tileMetrics(sav)
phiX <- mean(tMet$value[tMet$code == '300'])
clusterPF <- mean(tMet$value[tMet$code == '103'] / tMet$value[tMet$code == '102'], na.rm=T)
clusterDensity <- mean(tMet$value[tMet$code == '100'] / 1000)
clusterDensity_perLane <- sapply(split(tMet, tMet$lane), function(x) mean(x$value[x$code == '100'] / 1000))    
seq.metrics <- data.frame("totReads" = format(sum(amp.match.summary),  big.mark = ','),
                       "totReadsPassedQC" = format(sum(amp.match.summary[!(names(amp.match.summary) %in% 'no_align')]), big.mark = ','),
                       "phiX"=paste(round(phiX,2), "%"), "clusterPF"=paste(round(clusterPF*100,1), "%"),
                       "tot_phiX" = format(round((phiX / 100) * sum(amp.match.summary)), big.mark = ','),
                       "clustDensity"=paste(round(clusterDensity,1), 'K/mm^2'), 
                       "clustDensity_perLane"=paste(sapply(clusterDensity_perLane, round,1),collapse=' '))

# Read stats
fastq_dir <- paste0(rundir,"out/")

qcRes <- rqc(path = fastq_dir, pattern = ".fastq.gz", openBrowser=FALSE, workers = 6)
read_quality <- rqcCycleQualityBoxPlot(qcRes) + ylim(0,NA)
seq_cont_per_cycle <- rqcCycleBaseCallsLinePlot(qcRes)
read_freq_plot <- rqcReadFrequencyPlot(qcRes)
base_calls_plot <- rqcCycleBaseCallsLinePlot(qcRes)
cycl_qual_plot <- rqcCycleQualityPlot(qcRes)


params <- list(
  experiment = strsplit(rundir,"/") %>% unlist() %>% tail(1),
  run_info = run_info,
  season = season,
  amp.match.summary = amp.match.summary,
  sum_matched_df = sum_matched_df,
  results = results,
  seq.metrics = seq.metrics,
  classification = classification,
  # ind_na = ind_na,
  # qcRes = qcRes,
  read_quality = read_quality,
  cycl_qual_plot = cycl_qual_plot,
  seq_cont_per_cycle = seq_cont_per_cycle,
  read_freq_plot = read_freq_plot,
  base_calls_plot = base_calls_plot
)

rmarkdown::render(
  input = "../code/qc_report.Rmd",
  output_file = paste0(params$experiment,".pdf"),
  output_dir = rundir,
  params = params,
  envir = new.env(parent = globalenv())
)

exp_name <- strsplit(rundir,"/") %>% unlist() %>% tail(1)
pdf_name <- paste0(exp_name,".pdf")

Sys.time() - tic

# Results file:
# countTable.csv
# pdf_name
# sampleXLS
# SampleSheet.csv
# Analysis.Rmd
# run_info.csv
# LIMS_results.csv

