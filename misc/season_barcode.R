library(tidyverse)
setwd("/Users/kylekovary/Documents/GitHub/swabseq-analysis/")

bcs <- read_csv("hash_tables/384_plate_map.csv") %>% 
  separate(target, into = c("plate","row","column"), remove = F) %>% 
  mutate(plate = as.numeric(plate),
         row = as.numeric(row),
         column = as.numeric(column),
         row = LETTERS[row]) %>% 
  arrange(plate, row, column) %>% 
  mutate(mergedIndex = paste0(substr(index, 2, 11), substr(index2, 2, 11)))

combs <- read_csv("misc/SwabSeq_16_plates.csv")


create_season <- function(season){
  
  ind_plate_order <- combs %>% 
    filter(tolower(`Group Name`) == tolower(season)) %>% 
    pull(rev_plate)
  
  p1 <- bcs %>% 
    filter(plate == 1) %>% 
    mutate(index = bcs %>% filter(plate == ind_plate_order[1]) %>% pull(index))
  p2 <- bcs %>% 
    filter(plate == 2) %>% 
    mutate(index = bcs %>% filter(plate == ind_plate_order[2]) %>% pull(index))
  p3 <- bcs %>% 
    filter(plate == 3) %>% 
    mutate(index = bcs %>% filter(plate == ind_plate_order[3]) %>% pull(index))
  p4 <- bcs %>% 
    filter(plate == 4) %>% 
    mutate(index = bcs %>% filter(plate == ind_plate_order[4]) %>% pull(index))
  
  return(rbind(p1,p2,p3,p4) %>% mutate(season = season))
}

rbind(
  create_season("winter"),
  create_season("spring"),
  create_season("summer"),
  create_season("fall")
)

ss <- read.delim(paste0('misc/SampleSheet.csv'), stringsAsFactors=F, skip=14, sep=',') %>% 
  mutate(mergedIndex = paste0(index, index2)) %>% 
  as_tibble()

# Create file for LIMS
rbind(
  create_season("winter"),
  create_season("spring"),
  create_season("summer"),
  create_season("fall")
) %>% 
  left_join(dplyr::select(ss, -index, -index2), by = "mergedIndex") %>% 
  mutate(index = substr(index, 2, 11),
         index2 = substr(index2, 2, 11),
         mergedIndex = paste0(index, index2)) %>% 
  dplyr::select(-bc_set, -VirusUnits, -Plate_384_Number, -row, -column, -mergedIndex, -plate) %>%
  separate(target, into = c("plate_384", "row_384", "column_384")) %>% 
  separate(Plate_ID, into = c("rem", "plate_96"), sep = "Plate") %>% 
  dplyr::select(-rem) %>% 
  mutate(row_96 = substr(Sample_Well, 1,1),
         column_96 = as.numeric(substr(Sample_Well, 2, 3)),
         plate_96 = as.numeric(plate_96)) %>% 
  dplyr::rename(quadrant_color = Plate_384_Quadrant) %>% 
  dplyr::select(index, index2, plate_384, row_384, column_384, quadrant_color, plate_96, row_96, column_96, season) %>% 
  write_csv("~/Downloads/384_96_plate_map_seasons.csv")


# Create new SampleSheet.csv replacement
rbind(
  create_season("winter"),
  create_season("spring"),
  create_season("summer"),
  create_season("fall")
) %>% 
  left_join(dplyr::select(ss, -index, -index2), by = "mergedIndex") %>% 
  mutate(index = substr(index, 2, 11),
         index2 = substr(index2, 2, 11),
         mergedIndex = paste0(index, index2)) %>% 
  dplyr::select(-bc_set, -VirusUnits) %>% 
  dplyr::rename(pm = target) %>% 
  dplyr::select(index, index2, mergedIndex, pm, Plate_384_Number, Plate_384_Quadrant, Plate_ID, Sample_Well, Sample_ID) %>% 
  separate(pm, into = c("pm_384","row_384","col_384")) %>%
  mutate(row_384 = as.numeric(row_384),
         col_384 = as.numeric(col_384)) %>% 
  write_csv("~/Documents/GitHub/swabseq-analysis/misc/SampleSheet_v2.csv")

