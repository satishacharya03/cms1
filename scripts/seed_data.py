"""
MATRIXCMS - Academic Data Seeder
Populates the database with rich, realistic, academic data for Chandigarh CSE:
1. Users (Admin, Data Manager, Researcher, Public)
2. Expeditions (3 high-altitude and environmental research expeditions)
3. Reports (3 technical field reports with physical PDF documents)
4. Datasets (3 multi-parameter scientific datasets with physical CSV files)
5. Publications (3 peer-reviewed journal papers in IEEE, Glaciology, etc.)
6. Media (4 photo assets + 1 video asset with physical files)
7. Activities (3 institutional workshops, seminars, and symposia)
8. Generated Content (8 multi-platform outreach drafts: web_summary, tweet, linkedin, instagram)
"""

import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# Add project root to sys.path so app modules can be imported
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import settings
from app.database import engine, SessionLocal, Base
from app.auth import hash_password
from app.models import (
    User,
    UserRole,
    Expedition,
    ExpeditionStatus,
    Report,
    Dataset,
    Publication,
    Media,
    MediaType,
    Activity,
    ActivityType,
    GeneratedContent,
    PlatformType,
    ContentStatus,
)


def create_minimal_pdf(title: str, subtitle: str, author: str) -> bytes:
    """Generate a valid minimal PDF-1.4 file in pure Python bytes."""
    clean_title = title.replace("(", "\\(").replace(")", "\\)")[:70]
    clean_sub = subtitle.replace("(", "\\(").replace(")", "\\)")[:90]
    clean_auth = author.replace("(", "\\(").replace(")", "\\)")[:80]

    stream_content = (
        f"BT\n"
        f"/F1 16 Tf\n"
        f"50 720 Td\n"
        f"({clean_title}) Tj\n"
        f"0 -30 Td\n"
        f"/F1 11 Tf\n"
        f"({clean_sub}) Tj\n"
        f"0 -25 Td\n"
        f"/F1 10 Tf\n"
        f"({clean_auth}) Tj\n"
        f"0 -40 Td\n"
        f"(/F1 9 Tf\n)"
        f"(Department of Computer Science & Engineering - Chandigarh Research Portal) Tj\n"
        f"ET"
    )
    stream_bytes = stream_content.encode("latin-1", "replace")
    stream_len = len(stream_bytes)

    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length " + str(stream_len).encode("ascii") + b" >> stream\n"
        + stream_bytes + b"\nendstream\nendobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n0000000244 00000 n \n0000000400 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n500\n%%EOF\n"
    )
    return pdf_bytes


# Valid minimal JPEG (1x1 pixel image)
TINY_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010101004800480000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000010501010101010100000000000000000102030405060708090a0bffda0008010100003f00bf80ffd9"
)

# Valid minimal MP4 (ftyp + moov containers)
TINY_MP4 = bytes.fromhex(
    "000000186674797069736f6d0000020069736f6d69736f32617663310000000866726565000000086d646174"
)


def write_physical_files(storage_root: Path):
    """Create sample physical files in the storage hierarchy."""
    print("Writing physical asset files to storage root...")

    # 1. Reports (PDFs)
    report_files = [
        (
            storage_root / "reports" / "2025" / "06" / "hgds2025_glaciology_technical_report.pdf",
            "HGDS-2025 Field Technical Report",
            "Himalayan Glacial Dynamics & Sensor Network Deployment",
            "Dr. Vikramaditya Sharma, Er. Rohit Verma, Neha Thakur",
        ),
        (
            storage_root / "reports" / "2025" / "09" / "western_ghats_canopy_microclimate_report.pdf",
            "Western Ghats Canopy Survey Report",
            "Vertical Microclimate & Bioacoustic Heterogeneity",
            "Dr. Ananya Iyer, Dr. Siddharth Menon, Priya Nair",
        ),
        (
            storage_root / "reports" / "2025" / "12" / "sutlej_basin_hydrochemical_baseline_report.pdf",
            "Sutlej River Basin Hydrological Report",
            "Baseline Hydrochemical & Runoff Synthesis (Phase I)",
            "Dr. Rajeshwar Singh, Amit K. Patel, Dr. Sunita Kulkarni",
        ),
    ]
    for path, title, sub, author in report_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(create_minimal_pdf(title, sub, author))
        print(f"  [Report PDF] -> {path.relative_to(storage_root)}")

    # 2. Datasets (CSVs)
    # Dataset 1: Glacier Temperature Time-Series
    ds1_path = storage_root / "datasets" / "2025" / "06" / "glacier_temperature_timeseries_2025.csv"
    ds1_path.parent.mkdir(parents=True, exist_ok=True)
    ds1_rows = [
        "timestamp,sensor_id,elevation_m,borehole_depth_m,ice_temp_celsius,ambient_temp_celsius,solar_irradiance_wm2,battery_v"
    ]
    for day in range(1, 11):
        for hour in [0, 6, 12, 18]:
            ts = f"2025-05-{day:02d}T{hour:02d}:00:00Z"
            amb = -8.5 + (hour * 0.4)
            solar = 0.0 if (hour == 0 or hour == 18) else (450.0 if hour == 6 else 980.5)
            ds1_rows.append(f"{ts},CSG-BH01,4850,2.0,-4.25,{amb:.1f},{solar:.1f},3.96")
            ds1_rows.append(f"{ts},CSG-BH02,4850,5.0,-3.82,{amb:.1f},{solar:.1f},3.95")
            ds1_rows.append(f"{ts},CSG-BH03,4850,10.0,-2.15,{amb:.1f},{solar:.1f},3.94")
    ds1_path.write_text("\n".join(ds1_rows), encoding="utf-8")
    print(f"  [Dataset CSV] -> {ds1_path.relative_to(storage_root)} ({len(ds1_rows)} lines)")

    # Dataset 2: Western Ghats Canopy Humidity & Microclimate
    ds2_path = storage_root / "datasets" / "2025" / "09" / "canopy_humidity_microclimate_log.csv"
    ds2_path.parent.mkdir(parents=True, exist_ok=True)
    ds2_rows = [
        "timestamp,logger_id,stratum,relative_humidity_pct,air_temp_celsius,vpd_kpa,par_umol_m2_s"
    ]
    for day in range(1, 11):
        for hour in [0, 6, 12, 18]:
            ts = f"2025-08-{day:02d}T{hour:02d}:00:00Z"
            ds2_rows.append(f"{ts},WG-CAN-01,Ground_Understory,97.5,15.2,0.08,12.5")
            ds2_rows.append(f"{ts},WG-CAN-02,Mid_Subcanopy,92.1,17.4,0.18,145.0")
            ds2_rows.append(f"{ts},WG-CAN-03,Upper_Emergent,84.6,20.8,0.42,860.0")
    ds2_path.write_text("\n".join(ds2_rows), encoding="utf-8")
    print(f"  [Dataset CSV] -> {ds2_path.relative_to(storage_root)} ({len(ds2_rows)} lines)")

    # Dataset 3: Sutlej River Basin Watershed Flow Rate
    ds3_path = storage_root / "datasets" / "2025" / "11" / "watershed_flow_rate_timeseries.csv"
    ds3_path.parent.mkdir(parents=True, exist_ok=True)
    ds3_rows = [
        "timestamp,station_id,river_km,gauge_height_m,discharge_m3_s,turbidity_ntu,ph,conductivity_us_cm"
    ]
    for day in range(1, 11):
        for hour in [0, 6, 12, 18]:
            ts = f"2025-11-{day:02d}T{hour:02d}:00:00Z"
            ds3_rows.append(f"{ts},SUT-KHB-01,142.5,3.48,188.4,42.8,7.62,218.0")
            ds3_rows.append(f"{ts},SUT-RMP-02,185.0,4.12,245.8,55.4,7.58,232.5")
    ds3_path.write_text("\n".join(ds3_rows), encoding="utf-8")
    print(f"  [Dataset CSV] -> {ds3_path.relative_to(storage_root)} ({len(ds3_rows)} lines)")

    # 3. Media Files (4 Photos, 1 Video)
    media_files = [
        (storage_root / "media" / "2025" / "05" / "chhota_shigri_gateway_deployment.jpg", TINY_JPEG),
        (storage_root / "media" / "2025" / "05" / "borehole_thermistor_installation.jpg", TINY_JPEG),
        (storage_root / "media" / "2025" / "08" / "canopy_acoustic_sensor_tree.jpg", TINY_JPEG),
        (storage_root / "media" / "2025" / "11" / "sutlej_khhab_telemetry_station.jpg", TINY_JPEG),
        (storage_root / "media" / "2025" / "06" / "chhota_shigri_meltstream_timelapse.mp4", TINY_MP4),
    ]
    for path, raw_data in media_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw_data)
        print(f"  [Media {'Video' if path.suffix == '.mp4' else 'Photo'}] -> {path.relative_to(storage_root)}")


def seed_database():
    """Main database seeding routine."""
    print("=" * 65)
    print("MATRIXCMS Database Seeder - Chandigarh CSE Research Portal")
    print(f"Database: {settings.DATABASE_URL}")
    print(f"Storage:  {settings.STORAGE_ROOT}")
    print("=" * 65)

    # 1. Initialize schema
    print("Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)

    # 2. Prepare physical storage
    storage_root = Path(settings.STORAGE_ROOT).resolve()
    storage_root.mkdir(parents=True, exist_ok=True)
    write_physical_files(storage_root)

    db = SessionLocal()
    try:
        # 3. Clear existing seed data for idempotent rerun
        print("\nClearing previous records to ensure clean state...")
        db.query(GeneratedContent).delete()
        db.query(Media).delete()
        db.query(Publication).delete()
        db.query(Dataset).delete()
        db.query(Report).delete()
        db.query(Expedition).delete()
        db.query(Activity).delete()
        db.query(User).delete()
        db.commit()

        # -------------------------------------------------------------
        # 1. Users
        # -------------------------------------------------------------
        print("\n[1/8] Seeding Users...")
        users_data = [
            {
                "email": "admin@chandigarh.edu",
                "plain_password": "admin123",
                "role": UserRole.ADMIN.value,
            },
            {
                "email": "datamanager@chandigarh.edu",
                "plain_password": "data123",
                "role": UserRole.DATA_MANAGER.value,
            },
            {
                "email": "researcher@chandigarh.edu",
                "plain_password": "research123",
                "role": UserRole.RESEARCHER.value,
            },
            {
                "email": "student@chandigarh.edu",
                "plain_password": "student123",
                "role": UserRole.PUBLIC.value,
            },
        ]
        users = []
        for u in users_data:
            user = User(
                email=u["email"],
                hashed_password=hash_password(u["plain_password"]),
                role=u["role"],
            )
            db.add(user)
            users.append(user)
        db.commit()
        for u in users:
            print(f"  + User: {u.email:<30} Role: {u.role:<15}")

        # -------------------------------------------------------------
        # 2. Expeditions
        # -------------------------------------------------------------
        print("\n[2/8] Seeding Expeditions...")
        exp1 = Expedition(
            name="Himalayan Glacial Dynamics & Sensor Network Deployment (HGDS-2025)",
            start_date=date(2025, 4, 15),
            end_date=date(2025, 6, 30),
            region="Chhota Shigri & Bara Shigri Glaciers, Lahaul & Spiti, Himachal Pradesh",
            objectives=(
                "Deploy an array of edge-computing IoT temperature, ablation, and seismic sensors "
                "across high-altitude Himalayan glaciers; quantify seasonal melt velocity, supraglacial "
                "lake formation, and permafrost degradation under changing climate regimes."
            ),
            team_leader="Dr. Vikramaditya Sharma (Professor of CSE & Geospatial Computing, Chandigarh CSE)",
            status=ExpeditionStatus.COMPLETED.value,
        )
        exp2 = Expedition(
            name="Western Ghats High-Altitude Biodiversity & Microclimate Survey",
            start_date=date(2025, 8, 1),
            end_date=date(2025, 10, 15),
            region="Anamalai & Nilgiri Biosphere Reserves, Western Ghats, India",
            objectives=(
                "Deploy autonomous acoustic monitoring units and micro-meteorological logging "
                "stations across cloud forest canopies to study high-altitude biodiversity response "
                "to localized humidity gradients and vapor pressure deficits."
            ),
            team_leader="Dr. Ananya Iyer (Associate Professor of Environmental Informatics, Chandigarh CSE)",
            status=ExpeditionStatus.COMPLETED.value,
        )
        exp3 = Expedition(
            name="Sutlej River Basin Hydrological Monitoring & Water Quality Study",
            start_date=date(2025, 11, 1),
            end_date=date(2026, 3, 20),
            region="Upper Sutlej River Basin, Kinnaur & Shimla Districts, Himachal Pradesh",
            objectives=(
                "Establish real-time multiparametric telemetry along the upper Sutlej River to "
                "monitor glacial meltwater runoff, suspended sediment discharge, heavy metal concentrations, "
                "and flash flood vulnerability for downstream hydropower reservoirs."
            ),
            team_leader="Dr. Rajeshwar Singh (Lead Hydrological Systems Researcher, Chandigarh CSE)",
            status=ExpeditionStatus.ONGOING.value,
        )
        db.add_all([exp1, exp2, exp3])
        db.commit()
        db.refresh(exp1)
        db.refresh(exp2)
        db.refresh(exp3)
        print(f"  + Expedition 1 (ID {exp1.id}): {exp1.name}")
        print(f"  + Expedition 2 (ID {exp2.id}): {exp2.name}")
        print(f"  + Expedition 3 (ID {exp3.id}): {exp3.name}")

        # -------------------------------------------------------------
        # 3. Reports
        # -------------------------------------------------------------
        print("\n[3/8] Seeding Reports...")
        rep1 = Report(
            expedition_id=exp1.id,
            title="Himalayan Glacial Dynamics & Sensor Network Deployment: Technical Field Report & Initial Observations",
            authors="Dr. Vikramaditya Sharma, Er. Rohit Verma, Neha Thakur, Prof. K. R. Ramanathan (Chandigarh CSE & Collaborators)",
            abstract=(
                "This comprehensive technical report presents the deployment architecture and preliminary observations "
                "from the HGDS-2025 expedition across the Chhota Shigri glacier basin in Himachal Pradesh. We successfully "
                "deployed 18 LoRaWAN-enabled multi-depth temperature probes, 6 ultrasonic ablation stakes, and 2 solar-recharged "
                "edge telemetry gateways at elevations between 4,200m and 5,100m ASL. Initial acoustic and thermistor telemetry "
                "demonstrates elevated basal melt rates during late May 2025 and verifies sub-zero wireless transmission integrity "
                "across rugged terrain."
            ),
            file_path="reports/2025/06/hgds2025_glaciology_technical_report.pdf",
            doi="10.1016/j.hgds.2025.04.001",
            license="CC-BY-4.0",
            keywords="Glaciology, Himalayan Cryosphere, IoT Telemetry, LoRaWAN, Ice Dynamics, Climate Change",
            published=True,
        )
        rep2 = Report(
            expedition_id=exp2.id,
            title="Canopy Microclimate Gradients and Bioacoustic Density across Western Ghats High-Altitude Cloud Forests",
            authors="Dr. Ananya Iyer, Dr. Siddharth Menon, Priya Nair (Chandigarh CSE Department of Environmental Informatics)",
            abstract=(
                "Field assessment detailing the spatial heterogeneity of microclimates across three distinct canopy strata "
                "in the Nilgiri and Anamalai cloud forests. Using 24 synchronized solar-powered micro-loggers and directional "
                "ultrasonic microphones, our team recorded over 1,400 hours of synchronized high-fidelity bioacoustic data "
                "alongside high-resolution vapor pressure deficit (VPD) curves. Findings indicate localized thermal damping under "
                "intact canopies which directly correlates with endemic anuran vocal activity spikes."
            ),
            file_path="reports/2025/09/western_ghats_canopy_microclimate_report.pdf",
            doi="10.1016/j.wgbio.2025.08.002",
            license="CC-BY-4.0",
            keywords="Western Ghats, Canopy Microclimate, Bioacoustics, Cloud Forest, Biodiversity, Vapor Pressure Deficit",
            published=True,
        )
        rep3 = Report(
            expedition_id=exp3.id,
            title="Sutlej River Basin Hydrochemical and Glacial Meltwater Streamflow Monitoring: Phase-I Baseline Analysis",
            authors="Dr. Rajeshwar Singh, Amit K. Patel, Dr. Sunita Kulkarni (Chandigarh CSE Water Resources Research Group)",
            abstract=(
                "Phase-I technical synthesis reporting baseline hydrological discharge, isotope hydrograph separation, "
                "and continuous water quality metrics along a 180 km stretch of the Upper Sutlej River basin. Multiparametric "
                "sensor stations recorded electrical conductivity, turbidity, dissolved oxygen, and trace elemental concentrations "
                "across rapid seasonal meltwater transitions. The dataset establishes benchmark parameters for predicting "
                "downstream sediment influx during peak summer ablation."
            ),
            file_path="reports/2025/12/sutlej_basin_hydrochemical_baseline_report.pdf",
            doi="10.1016/j.sutlej.2025.12.003",
            license="CC-BY-4.0",
            keywords="Sutlej Basin, Hydrology, Water Quality, Glacial Runoff, Hydrochemistry, Sediment Transport",
            published=True,
        )
        db.add_all([rep1, rep2, rep3])
        db.commit()
        db.refresh(rep1)
        db.refresh(rep2)
        db.refresh(rep3)
        print(f"  + Report 1 (ID {rep1.id}): {rep1.title[:65]}...")
        print(f"  + Report 2 (ID {rep2.id}): {rep2.title[:65]}...")
        print(f"  + Report 3 (ID {rep3.id}): {rep3.title[:65]}...")

        # -------------------------------------------------------------
        # 4. Datasets
        # -------------------------------------------------------------
        print("\n[4/8] Seeding Scientific Datasets...")
        ds1 = Dataset(
            expedition_id=exp1.id,
            title="Chhota Shigri Glacier Multi-Depth Borehole Ice Temperature Time-Series (2025)",
            variables="timestamp, sensor_id, elevation_m, borehole_depth_m, ice_temp_celsius, ambient_temp_celsius, solar_irradiance_wm2, battery_v",
            units="ISO-8601, string, meters, meters, degrees Celsius, degrees Celsius, W/m^2, Volts",
            temporal_coverage="2025-05-01T00:00:00Z to 2025-05-10T18:00:00Z (Hourly telemetry intervals)",
            spatial_coverage="Chhota Shigri Glacier, Lahaul & Spiti, Himachal Pradesh (32.284° N, 77.519° E, 4850m ASL)",
            file_path="datasets/2025/06/glacier_temperature_timeseries_2025.csv",
            doi="10.5281/zenodo.1082501",
            license="CC-BY-4.0",
            keywords="glaciology, ice temperature, boreholes, cryosphere, iot, himalayas, time-series",
            published=True,
        )
        ds2 = Dataset(
            expedition_id=exp2.id,
            title="Western Ghats Cloud Forest Canopy Humidity and Microclimate Sensor Logs",
            variables="timestamp, logger_id, stratum, relative_humidity_pct, air_temp_celsius, vpd_kpa, par_umol_m2_s",
            units="ISO-8601, string, string, percent (%), degrees Celsius, kilopascals (kPa), umol/(m^2*s)",
            temporal_coverage="2025-08-01T00:00:00Z to 2025-08-10T18:00:00Z (Synchronized logging intervals)",
            spatial_coverage="Anamalai Tiger Reserve & Valparai Plateau, Tamil Nadu (10.328° N, 76.953° E, 1600m - 2200m ASL)",
            file_path="datasets/2025/09/canopy_humidity_microclimate_log.csv",
            doi="10.5281/zenodo.1082502",
            license="CC-BY-4.0",
            keywords="canopy microclimate, humidity, vapor pressure deficit, cloud forest, bioacoustics, environmental sensor",
            published=True,
        )
        ds3 = Dataset(
            expedition_id=exp3.id,
            title="Upper Sutlej River Basin Watershed Streamflow Discharge and Water Quality Time-Series",
            variables="timestamp, station_id, river_km, gauge_height_m, discharge_m3_s, turbidity_ntu, ph, conductivity_us_cm",
            units="ISO-8601, string, kilometers, meters, m^3/s, NTU, pH units, uS/cm",
            temporal_coverage="2025-11-01T00:00:00Z to 2025-11-10T18:00:00Z (Multiparametric telemetry intervals)",
            spatial_coverage="Upper Sutlej Basin, Kinnaur District, Himachal Pradesh (31.758° N, 78.591° E to 31.420° N, 77.630° E)",
            file_path="datasets/2025/11/watershed_flow_rate_timeseries.csv",
            doi="10.5281/zenodo.1082503",
            license="CC-BY-4.0",
            keywords="hydrology, river basin, discharge, streamflow, water quality, turbidity, sediment transport, sutlej",
            published=True,
        )
        db.add_all([ds1, ds2, ds3])
        db.commit()
        db.refresh(ds1)
        db.refresh(ds2)
        db.refresh(ds3)
        print(f"  + Dataset 1 (ID {ds1.id}): {ds1.title[:65]}...")
        print(f"  + Dataset 2 (ID {ds2.id}): {ds2.title[:65]}...")
        print(f"  + Dataset 3 (ID {ds3.id}): {ds3.title[:65]}...")

        # -------------------------------------------------------------
        # 5. Publications
        # -------------------------------------------------------------
        print("\n[5/8] Seeding Peer-Reviewed Publications...")
        pub1 = Publication(
            expedition_id=exp1.id,
            title="LoRaWAN-Based Telemetry for Autonomous Cryospheric Monitoring in Extreme Himalayan Topography",
            authors="Vikramaditya Sharma, Rohit Verma, and K. R. Ramanathan",
            journal="IEEE Transactions on Geoscience and Remote Sensing",
            year=2025,
            doi="10.1109/TGRS.2025.3389012",
            abstract=(
                "Autonomous cryospheric sensor networks in high-altitude glaciated basins suffer from severe power constraints, "
                "extreme sub-zero drift, and complex non-line-of-sight propagation. In this study, researchers from the Department "
                "of CSE at Chandigarh present a resilient edge-computing telemetry framework validated across the Chhota Shigri "
                "glacier (4,200m–5,100m ASL). Utilizing 868 MHz LoRaWAN links with customized adaptive data rate (ADR) algorithms "
                "and ultra-low-power sleep cycles, our sensor nodes maintained 99.4% packet delivery across 8.4 km obstructed "
                "alpine channels. We discuss hardware ruggedization against rime ice accumulation and validate borehole thermal "
                "models against multi-depth thermistor strings."
            ),
            link="https://doi.org/10.1109/TGRS.2025.3389012",
            published=True,
        )
        pub2 = Publication(
            expedition_id=exp2.id,
            title="Vertical Stratification of Microclimate and Bioacoustic Diversity in Western Ghats Shola-Cloud Forest Ecotones",
            authors="Ananya Iyer, Siddharth Menon, Priya Nair, and Rajeshwar Singh",
            journal="Journal of Ecology and Environmental Informatics",
            year=2025,
            doi="10.1016/j.ecolinf.2025.102450",
            abstract=(
                "Tropical montane cloud forests (Shola ecosystems) of the Western Ghats represent critical biodiversity hotspots "
                "vulnerable to microclimatic shifts. We present empirical findings from synchronized canopy sensor arrays deployed "
                "across three vertical strata in the Anamalai Highlands. Automated convolutional neural network (CNN) detection "
                "applied to 1,400 hours of acoustic recordings demonstrated that endemic bird and anuran vocal activity peaked "
                "within narrow vapor pressure deficit (VPD) corridors (<0.35 kPa) preserved solely beneath intact upper canopies, "
                "underscoring the buffering capacity of primary forest against regional warming."
            ),
            link="https://doi.org/10.1016/j.ecolinf.2025.102450",
            published=True,
        )
        pub3 = Publication(
            expedition_id=exp3.id,
            title="Coupled Hydrochemical and Machine Learning Modeling of Glacial Runoff in the Upper Sutlej Basin",
            authors="Rajeshwar Singh, Amit K. Patel, Sunita Kulkarni, and Vikramaditya Sharma",
            journal="Journal of Glaciology",
            year=2025,
            doi="10.1017/jog.2025.77",
            abstract=(
                "Predicting meltwater discharge and sediment discharge in the trans-Himalayan Sutlej River is essential for "
                "downstream water security and hydropower management. Combining in-situ telemetry with hydrochemical isotopic "
                "tracers (delta-18O and delta-D) and an attention-based LSTM architecture developed at Chandigarh CSE, we "
                "disentangle ice melt, snowmelt, and baseflow contributions. The model achieves an NSE score of 0.92 during the "
                "peak ablation period and reliably forecasts flash discharge events triggered by subglacial drainage pulses."
            ),
            link="https://doi.org/10.1017/jog.2025.77",
            published=True,
        )
        db.add_all([pub1, pub2, pub3])
        db.commit()
        db.refresh(pub1)
        db.refresh(pub2)
        db.refresh(pub3)
        print(f"  + Publication 1 (ID {pub1.id}): {pub1.title[:65]}...")
        print(f"  + Publication 2 (ID {pub2.id}): {pub2.title[:65]}...")
        print(f"  + Publication 3 (ID {pub3.id}): {pub3.title[:65]}...")

        # -------------------------------------------------------------
        # 6. Media (4 Photos, 1 Video)
        # -------------------------------------------------------------
        print("\n[6/8] Seeding Media Assets...")
        med1 = Media(
            expedition_id=exp1.id,
            media_type=MediaType.PHOTO.value,
            caption="Deployment of autonomous solar-powered LoRaWAN gateway station at 4,850m elevation on Chhota Shigri Glacier ridge.",
            location="Chhota Shigri Glacier Ridge, Lahaul-Spiti, Himachal Pradesh (32.284° N, 77.519° E)",
            timestamp=datetime(2025, 5, 12, 11, 30, tzinfo=timezone.utc),
            file_path="media/2025/05/chhota_shigri_gateway_deployment.jpg",
            tags="glacier, telemetry, lora, solar, high-altitude, sensors, fieldwork, himalayas",
            license="CC-BY-4.0",
            published=True,
        )
        med2 = Media(
            expedition_id=exp1.id,
            media_type=MediaType.PHOTO.value,
            caption="Research engineers installing thermistor string inside an 8-meter steam-drilled borehole on glacier ablation zone.",
            location="Bara Shigri Ablation Zone, Lahaul & Spiti (32.245° N, 77.592° E)",
            timestamp=datetime(2025, 5, 20, 14, 15, tzinfo=timezone.utc),
            file_path="media/2025/05/borehole_thermistor_installation.jpg",
            tags="ice-drilling, thermistors, cryosphere, ablation, fieldwork, expedition, glaciology",
            license="CC-BY-4.0",
            published=True,
        )
        med3 = Media(
            expedition_id=exp2.id,
            media_type=MediaType.PHOTO.value,
            caption="Bioacoustic monitoring node and microclimate sensor mounted 28 meters above ground in Western Ghats evergreen canopy.",
            location="Anamalai Tiger Reserve, Valparai Plateau, Tamil Nadu (10.328° N, 76.953° E)",
            timestamp=datetime(2025, 8, 18, 9, 45, tzinfo=timezone.utc),
            file_path="media/2025/08/canopy_acoustic_sensor_tree.jpg",
            tags="cloud-forest, bioacoustics, canopy-sensors, western-ghats, microclimate, biodiversity",
            license="CC-BY-4.0",
            published=True,
        )
        med4 = Media(
            expedition_id=exp3.id,
            media_type=MediaType.PHOTO.value,
            caption="Automated telemetry gauging station capturing turbulent glacial meltwater runoff along the Upper Sutlej River gorge.",
            location="Khhab Confluence, Kinnaur, Himachal Pradesh (31.758° N, 78.591° E)",
            timestamp=datetime(2025, 11, 24, 16, 20, tzinfo=timezone.utc),
            file_path="media/2025/11/sutlej_khhab_telemetry_station.jpg",
            tags="hydrology, streamflow, runoff, sutlej-river, water-quality, telemetry, sediment",
            license="CC-BY-4.0",
            published=True,
        )
        med5 = Media(
            expedition_id=exp1.id,
            media_type=MediaType.VIDEO.value,
            caption="Time-lapse video recording supraglacial melt stream carving through moraine ice and sensor station telemetry transmission.",
            location="Chhota Shigri Glacier Lower Tongue (32.290° N, 77.511° E)",
            timestamp=datetime(2025, 6, 2, 10, 0, tzinfo=timezone.utc),
            file_path="media/2025/06/chhota_shigri_meltstream_timelapse.mp4",
            tags="time-lapse, meltwater, supraglacial, ice-stream, drone-survey, video, cryosphere",
            license="CC-BY-4.0",
            published=True,
        )
        db.add_all([med1, med2, med3, med4, med5])
        db.commit()
        db.refresh(med1)
        db.refresh(med2)
        db.refresh(med3)
        db.refresh(med4)
        db.refresh(med5)
        print(f"  + Media 1 [PHOTO] (ID {med1.id}): {med1.caption[:60]}...")
        print(f"  + Media 2 [PHOTO] (ID {med2.id}): {med2.caption[:60]}...")
        print(f"  + Media 3 [PHOTO] (ID {med3.id}): {med3.caption[:60]}...")
        print(f"  + Media 4 [PHOTO] (ID {med4.id}): {med4.caption[:60]}...")
        print(f"  + Media 5 [VIDEO] (ID {med5.id}): {med5.caption[:60]}...")

        # -------------------------------------------------------------
        # 7. Activities
        # -------------------------------------------------------------
        print("\n[7/8] Seeding Institutional Activities...")
        act1 = Activity(
            activity_type=ActivityType.WORKSHOP.value,
            title="Workshop on Distributed Sensor Networks in Mountainous Terrain",
            date=date(2025, 7, 10),
            description=(
                "A hands-on technical workshop organized by the Department of Computer Science & Engineering, "
                "Chandigarh. Faculty, postgraduates, and industry participants explored low-power mesh networking, "
                "satellite backhaul, LoRaWAN deployment strategies, and hardware weather-proofing under sub-zero conditions "
                "based on lessons from the HGDS-2025 Himalayan expedition."
            ),
            related_expedition_ids=[exp1.id],
            published=True,
        )
        act2 = Activity(
            activity_type=ActivityType.EVENT.value,
            title="Public Seminar: Climate Data Science at Chandigarh CSE",
            date=date(2025, 9, 25),
            description=(
                "An open public seminar hosted at Chandigarh CSE Auditorium, open to researchers, students, and citizens. "
                "Dr. Vikramaditya Sharma and Dr. Ananya Iyer shared preliminary insights from Himalayan cryospheric sensors "
                "and Western Ghats bioacoustic monitors, emphasizing the critical role of open machine learning pipelines "
                "in tracking India's climate vulnerabilities."
            ),
            related_expedition_ids=[exp1.id, exp2.id],
            published=True,
        )
        act3 = Activity(
            activity_type=ActivityType.EVENT.value,
            title="Symposium on Open Science & FAIR Data Standards",
            date=date(2025, 11, 15),
            description=(
                "A national symposium dedicated to advancing FAIR (Findable, Accessible, Interoperable, Reusable) "
                "scientific data practices across environmental and computational engineering disciplines. Keynote addresses "
                "focused on institutional repository architecture, automated DOI assignment, open dataset licenses, and "
                "reproducibility in high-mountain hydrological modeling."
            ),
            related_expedition_ids=[exp1.id, exp2.id, exp3.id],
            published=True,
        )
        db.add_all([act1, act2, act3])
        db.commit()
        db.refresh(act1)
        db.refresh(act2)
        db.refresh(act3)
        print(f"  + Activity 1 (ID {act1.id}): {act1.title}")
        print(f"  + Activity 2 (ID {act2.id}): {act2.title}")
        print(f"  + Activity 3 (ID {act3.id}): {act3.title}")

        # -------------------------------------------------------------
        # 8. Generated Content (Drafts across platforms & statuses)
        # -------------------------------------------------------------
        print("\n[8/8] Seeding Generated Content Drafts...")
        gc_items = [
            # Report 1 Drafts
            GeneratedContent(
                source_type="report",
                source_id=rep1.id,
                platform=PlatformType.WEB_SUMMARY.value,
                content=(
                    "Chandigarh CSE researchers have published their technical field report on the HGDS-2025 Himalayan expedition. "
                    "Deploying 18 LoRaWAN sensor nodes up to 5,100m ASL across the Chhota Shigri glacier, the team demonstrated "
                    "robust telemetry for continuous ice melt and thermistor monitoring in extreme alpine environments."
                ),
                status=ContentStatus.APPROVED.value,
            ),
            GeneratedContent(
                source_type="report",
                source_id=rep1.id,
                platform=PlatformType.TWEET.value,
                content=(
                    "🏔️ Exciting update from #ChandigarhCSE! Our HGDS-2025 expedition deployed 18 LoRaWAN sensor nodes across "
                    "Chhota Shigri Glacier at 5,100m ASL. Real-time ice melt & temperature telemetry is now live! "
                    "Read the report: https://portal.chandigarh.edu/reports/1 📡❄️ #OpenScience #Glaciology"
                ),
                status=ContentStatus.APPROVED.value,
            ),
            GeneratedContent(
                source_type="report",
                source_id=rep1.id,
                platform=PlatformType.LINKEDIN.value,
                content=(
                    "We are thrilled to announce the publication of our field report: 'Himalayan Glacial Dynamics & Sensor Network "
                    "Deployment (HGDS-2025)'.\n\nConducted by researchers at the Department of Computer Science & Engineering (Chandigarh) "
                    "in collaboration with cryospheric glaciologists, this initiative deployed an edge-computing IoT sensor mesh across "
                    "the Chhota Shigri glacier basin (4,200m–5,100m ASL).\n\nKey highlights:\n• 18 custom LoRaWAN sensor nodes\n"
                    "• Borehole thermistor strings up to 10m depth\n• 99.4% packet reception rate across alpine ridges\n\n"
                    "Full open-access technical report and datasets are available on our portal."
                ),
                status=ContentStatus.PENDING_REVIEW.value,
            ),
            GeneratedContent(
                source_type="report",
                source_id=rep1.id,
                platform=PlatformType.INSTAGRAM.value,
                content=(
                    "Scaling the Himalayas for Climate Science! 🏔️❄️\n\nThe Chandigarh CSE team completed the HGDS-2025 expedition across "
                    "Chhota Shigri glacier at 5,100m elevation. Braving sub-zero winds, our researchers deployed edge-computing sensors "
                    "to track glacial melt in real-time.\n\nSwipe to see our telemetry stations in action 👉\n\n"
                    "#ChandigarhCSE #Himalayas #GlacierResearch #ClimateTech #Fieldwork #IoT #EngineeringForGood"
                ),
                status=ContentStatus.PENDING_REVIEW.value,
            ),
            # Dataset 1 Drafts
            GeneratedContent(
                source_type="dataset",
                source_id=ds1.id,
                platform=PlatformType.WEB_SUMMARY.value,
                content=(
                    "Hourly borehole ice temperature and micrometeorological dataset collected during the HGDS-2025 expedition. "
                    "Covers elevations from 4,300m to 5,050m ASL with multi-depth thermistor readings, published under CC-BY-4.0 open data license."
                ),
                status=ContentStatus.APPROVED.value,
            ),
            GeneratedContent(
                source_type="dataset",
                source_id=ds1.id,
                platform=PlatformType.TWEET.value,
                content=(
                    "📊 New Open Dataset Alert! Access hourly borehole ice temperatures & surface solar irradiance from Chhota Shigri "
                    "Glacier (HGDS-2025). Free to download & analyze under CC-BY-4.0: https://portal.chandigarh.edu/datasets/1 🧊📈 "
                    "#OpenData #Cryosphere #ChandigarhCSE"
                ),
                status=ContentStatus.PENDING_REVIEW.value,
            ),
            # Activity 1 Drafts
            GeneratedContent(
                source_type="activity",
                source_id=act1.id,
                platform=PlatformType.LINKEDIN.value,
                content=(
                    "Highlights from our recent 'Workshop on Distributed Sensor Networks in Mountainous Terrain' at Chandigarh CSE! "
                    "Over 80 researchers gathered to discuss ruggedized hardware, low-power mesh protocols, and practical lessons "
                    "from alpine deployment. Thank you to all participants who made it a resounding success!"
                ),
                status=ContentStatus.APPROVED.value,
            ),
            GeneratedContent(
                source_type="activity",
                source_id=act1.id,
                platform=PlatformType.TWEET.value,
                content=(
                    "Recap: Incredible discussions today at the #ChandigarhCSE Workshop on Mountain Sensor Networks! Great insights on "
                    "satellite telemetry, solar reliability, and rugged edge nodes. 🏔️💻 #TechForGood #IoT"
                ),
                status=ContentStatus.PENDING_REVIEW.value,
            ),
        ]
        db.add_all(gc_items)
        db.commit()
        for gc in gc_items:
            db.refresh(gc)
            print(f"  + Draft (ID {gc.id:<2}): Source: {gc.source_type:<8} ID: {gc.source_id:<2} Platform: {gc.platform:<12} Status: {gc.status}")

        print("\n" + "=" * 65)
        print("DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 65)
        print("\nSummary of Seeded Entities:")
        print(f"  • Users:             {db.query(User).count()} (Admin, Data Manager, Researcher, Public)")
        print(f"  • Expeditions:       {db.query(Expedition).count()}")
        print(f"  • Field Reports:     {db.query(Report).count()} (with sample PDF files in storage)")
        print(f"  • Datasets:          {db.query(Dataset).count()} (with sample CSV files in storage)")
        print(f"  • Publications:      {db.query(Publication).count()}")
        print(f"  • Media Assets:      {db.query(Media).count()} (4 Photos + 1 Video with sample files)")
        print(f"  • Activities:        {db.query(Activity).count()}")
        print(f"  • Generated Drafts:  {db.query(GeneratedContent).count()} (Pending review & Approved)")
        print("\nDemo Login Credentials:")
        print("  1. Admin:        admin@chandigarh.edu       / admin123")
        print("  2. Data Manager: datamanager@chandigarh.edu / data123")
        print("  3. Researcher:   researcher@chandigarh.edu  / research123")
        print("  4. Public User:  student@chandigarh.edu     / student123")
        print("=" * 65)

    except Exception as exc:
        db.rollback()
        print(f"\n[ERROR] Seeding failed: {exc}", file=sys.stderr)
        raise exc
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
