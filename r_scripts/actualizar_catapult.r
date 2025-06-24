print("✅ INICIO del script R")

# =================== PAQUETES ===================
if (!require("catapultR")) install.packages("catapultR", repos = "https://cloud.r-project.org")
if (!require("googlesheets4")) install.packages("googlesheets4", repos = "https://cloud.r-project.org")
if (!require("readxl")) install.packages("readxl", repos = "https://cloud.r-project.org")
if (!require("lubridate")) install.packages("lubridate", repos = "https://cloud.r-project.org")
if (!require("dplyr")) install.packages("dplyr", repos = "https://cloud.r-project.org")
if (!require("slider")) install.packages("slider", repos = "https://cloud.r-project.org")
if (!require("purrr")) install.packages("purrr", repos = "https://cloud.r-project.org")

library(catapultR)
library(dplyr)
library(lubridate)
library(googlesheets4)
library(readxl)
library(slider)
library(purrr)

# =================== CONFIGURACIÓN ===================
ruta_token <- "credentials/catapult_token.txt"
ruta_credenciales <- "credentials/credentials.json"
dias_hacia_atras <- 1
url_google_sheet <- "https://docs.google.com/spreadsheets/d/11ntkguPaXrRHnZX9kNguLODWBjpupPz4s8gdbZ75_Ck/edit"
nombre_hoja <- "Hoja 1"

# =================== ENTRADA STREAMLIT ===================
day_type <- Sys.getenv("DAY_TYPE", unset = "PRE")
day_tipe <- Sys.getenv("DAY_TIPE", unset = "TRAINING")

# =================== TOKEN CATAPULT ===================
print("🔑 Authenticating with Catapult...")
raw_token <- readLines(ruta_token)
token <- ofCloudCreateToken(sToken = as.character(raw_token), sRegion = "EMEA")

# =================== EXTRACCIÓN DE DATOS ===================
print("⬇️ Fetching data...")
datos <- ofCloudGetStatistics(
  token,
  params = c(
    "athlete_name", "date", "activity_name", "position_name", "total_distance", "total_duration", "total_player_load",
    "velocity_band3_total_distance", "velocity_band4_total_distance", "velocity_band5_total_distance", "velocity_band6_total_distance",
    "velocity_band4_average_effort_count", "velocity_band5_average_effort_count", "velocity_band6_average_effort_count",
    "gen2_acceleration_band7plus_total_effort_count", "gen2_acceleration_band2plus_total_effort_count",
    "metabolic_power_band3_total_distance", "metabolic_power_band4_total_distance",
    "metabolic_power_band5_total_distance", "metabolic_power_band6_total_distance",
    "max_vel", "max_effort_acceleration", "max_effort_deceleration",
    "running_imbalance", "running_deviation"
  ),
  groupby = c("athlete", "period"),
  filters = list(name = "lastActivities", comparison = "=", values = dias_hacia_atras)
)

# =================== CONVERSIÓN SEGURA DE FECHAS ===================
print("📆 Fixing date format...")
datos$date <- as.Date(datos$date, tryFormats = c("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"))

# =================== AGRUPACIÓN Y MÉTRICAS ===================
print("🧮 Calculating metrics...")
datos_sesion <- datos %>%
  group_by(athlete_name, date, activity_name) %>%
  summarise(
    position = first(position_name),
    session = first(activity_name),
    total_distance = sum(total_distance, na.rm = TRUE),
    total_duration = sum(total_duration, na.rm = TRUE) / 60,
    total_player_load = sum(total_player_load, na.rm = TRUE),
    MSR_dist = sum(velocity_band6_total_distance + velocity_band4_total_distance + velocity_band5_total_distance, na.rm = TRUE),
    HSR_dist = sum(velocity_band5_total_distance, na.rm = TRUE),
    Sprint_dist = sum(velocity_band6_total_distance, na.rm = TRUE),
    hir_dist = sum(velocity_band5_total_distance + velocity_band6_total_distance, na.rm = TRUE),
    hir_eff = sum(velocity_band5_average_effort_count + velocity_band6_average_effort_count, na.rm = TRUE),
    HSR_eff = sum(velocity_band5_average_effort_count, na.rm = TRUE),
    Sprint_eff = sum(velocity_band6_average_effort_count, na.rm = TRUE),
    acc_eff_3 = sum(gen2_acceleration_band7plus_total_effort_count, na.rm = TRUE),
    dcc_eff_3 = sum(gen2_acceleration_band2plus_total_effort_count, na.rm = TRUE),
    HMLD = sum(metabolic_power_band3_total_distance + metabolic_power_band4_total_distance +
                 metabolic_power_band5_total_distance + metabolic_power_band6_total_distance, na.rm = TRUE),
    max_speed = max(max_vel, na.rm = TRUE),
    max_accel = max(max_effort_acceleration, na.rm = TRUE),
    max_decc = min(max_effort_deceleration, na.rm = TRUE),
    por_desequilibrio_pisada = first(running_deviation),
    simetria_carrera = first(running_imbalance),
    .groups = "drop"
  ) %>%
  mutate(
    m_min = total_distance / total_duration,
    spr_min = Sprint_dist / total_duration,
    acc_3_min = acc_eff_3 / total_duration,
    dcc_3_min = dcc_eff_3 / total_duration,
    hir_min = hir_dist / total_duration,
    hir_eff_min = hir_eff / total_duration,
    spr_eff_min = Sprint_eff / total_duration,
    HMLD_min = HMLD / total_duration,
    day_type = toupper(day_type),
    day_tipe = day_tipe
  ) %>%
  select(-activity_name)

# =================== GOOGLE SHEETS ===================
print("📥 Reading existing sheet...")
gs4_auth(path = ruta_credenciales)
df_existente <- read_sheet(url_google_sheet, sheet = nombre_hoja)
df_existente$date <- as.Date(df_existente$date, tryFormats = c("%Y-%m-%d", "%d/%m/%Y"))

# =================== MÁXIMOS INDIVIDUALES ===================
print("📊 Calculating player max values...")
maximos_ind <- df_existente %>%
  group_by(athlete_name) %>%
  summarise(
    ind_max_speed = max(max_speed, na.rm = TRUE),
    ind_max_acc = max(max_accel, na.rm = TRUE),
    ind_max_dcc = min(max_decc, na.rm = TRUE),
    .groups = "drop"
  )

datos_sesion <- datos_sesion %>%
  left_join(maximos_ind, by = "athlete_name") %>%
  mutate(
    por_vel = ifelse(ind_max_speed > 0, max_speed / ind_max_speed, NA),
    por_acc = ifelse(ind_max_acc > 0, max_accel / ind_max_acc, NA),
    por_dcc = ifelse(ind_max_dcc != 0, max_decc / ind_max_dcc, NA)
  )

# =================== ACWR ===================
print("📈 Calculando ACWR...")
df_full <- bind_rows(df_existente, datos_sesion) %>%
  mutate(date = as.Date(date)) %>%
  arrange(athlete_name, date)

df_full <- df_full %>%
  group_by(athlete_name) %>%
  mutate(
    acute_dist = map_dbl(date, ~sum(total_distance[date >= .x - 6 & date <= .x], na.rm = TRUE)),
    chronic_dist = map_dbl(date, ~sum(total_distance[date >= .x - 27 & date <= .x], na.rm = TRUE)),
    acwr_dist = ifelse(chronic_dist > 0, acute_dist / (chronic_dist / 4), NA),

    acute_dur = map_dbl(date, ~sum(total_duration[date >= .x - 6 & date <= .x], na.rm = TRUE)),
    chronic_dur = map_dbl(date, ~sum(total_duration[date >= .x - 27 & date <= .x], na.rm = TRUE)),
    acwr_dur = ifelse(chronic_dur > 0, acute_dur / (chronic_dur / 4), NA),

    acute_hir = map_dbl(date, ~sum(hir_dist[date >= .x - 6 & date <= .x], na.rm = TRUE)),
    chronic_hir = map_dbl(date, ~sum(hir_dist[date >= .x - 27 & date <= .x], na.rm = TRUE)),
    acwr_hir = ifelse(chronic_hir > 0, acute_hir / (chronic_hir / 4), NA),

    acute_acc = map_dbl(date, ~sum(acc_eff_3[date >= .x - 6 & date <= .x], na.rm = TRUE)),
    chronic_acc = map_dbl(date, ~sum(acc_eff_3[date >= .x - 27 & date <= .x], na.rm = TRUE)),
    acwr_acc = ifelse(chronic_acc > 0, acute_acc / (chronic_acc / 4), NA)
  ) %>%
  ungroup()

# =================== FUSIÓN FINAL Y SUBIDA ===================
print("🔗 Fusionando y subiendo...")
df_total <- df_full %>%
  distinct(athlete_name, date, session, .keep_all = TRUE) %>%
  arrange(date, athlete_name)

range_write(ss = url_google_sheet, data = df_total, sheet = nombre_hoja, col_names = TRUE, reformat = FALSE)

print("✅ FINALIZADO")

