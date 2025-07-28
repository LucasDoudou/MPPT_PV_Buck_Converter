MPPT_PV_Buck_Converter
======================

This project implements a Maximum Power Point Tracking (MPPT) Photovoltaic (PV) Buck Converter.  
It was completed as part of EE113B at the University of California, Berkeley (~4 months).

Special thanks:
Prof. Jessica Boles  
TAs: Tahmid Mahbub & Elisa Krause  

Key Features:
- High-efficiency synchronous buck DC-DC converter (>96% efficiency)
- Input Voltage: 16V–24V (nominal 20V)
- Output Voltage: 12V regulated
- Output Power: 50W–100W
- Switching Frequency: 100kHz
- MPPT algorithm: Perturb & Observe (P&O) for steady-state and dynamic tracking
- Implemented using the Texas Instruments C2000 microcontroller for real-time PWM-based control
- Fully custom PCB layout
- Efficiency Calculation: +15% at 4 corners (50W/100W + 16V/24V) and +40% at nominal point (100W + 20V)
- This project utilizes a selection of off-the-shelf and cost-effective components, 61.06$ per board

License:
This project is intended for academic and educational purposes only.  
You are free to reference and use this project with proper attribution.  
For any commercial use, please contact the author.

For full design details and results, please see the final report (PDF) in the /docs folder.
