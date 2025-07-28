/*
 * AUTHOR: RAHUL IYER (rkiyer@berkeley.edu)
 *
 * This project initializes the EPWM and ADC peripherals to interface with a buck converter
 *
 * As a starting point for exploring digital control implementation on the C2000, we will implement
 * the controller in an infinite loop inside the main function.
 *
 * The ADC peripheral is configured to periodically sample V_in, V_out, I_in, and I_out once per PWM period.
 * This setup allows us to avoid writing code to manually start and wait for the ADC conversions inside our
 * control loop. This sampling setup will also be appropriate for interrupt-driven controller implementations.
 */
// OK version

#include "F28x_Project.h" // this includes all headers needed to interact with peripherals (ADC, EPWM, etc.)
#include "cpu1_init.h"

// #define ADC_VREF 3.0
// #define ADC_MAX 4095.0  // 12-bit ADC max value

// volatile Uint16 adc_raw;
// volatile float adc_vin;
volatile Uint16 adc_raw_vout; // 0->4095
volatile Uint16 adc_raw_iout;
volatile float adc_vout; // 0->3
volatile float adc_iout; // 0->3

volatile Uint16 duty_cmp = EPWM_CMP_INIT;
volatile float duty = 0.5;

volatile Uint16 deadtime_rise = EPWM_DEADTIME;
volatile Uint16 deadtime_fall = EPWM_DEADTIME;



int main(void)


{

    InitSysCtrl(); //Initialize SYSCTL (PLL, Watchdog, etc.)

#ifdef LAUNCHPAD // include this define in project settings if using a LaunchPad
    EALLOW;
    ClkCfgRegs.PERCLKDIVSEL.bit.EPWMCLKDIV = 0; // remove /2 clock division for LaunchPad to make calculations consistent with ControlCard
    EDIS;
#endif


    InitGpio();    //Initialize GPIO register states

    configure_GPIO();               // configure GPIO settings

    DINT;                           // Disable ST1.INTM
    IER = 0x0000;                   // Disable CPU interrupts
    IFR = 0x0000;                   // Clear all CPU interrupt flags

    InitPieCtrl();                  // Initialize PIE control registers
    InitPieVectTable();             // Initialize PIE vector table to default ISR locations...
                                    // This will typically be overwritten later

    configure_ADC();                // configure ADC settings
    configure_EPWM();               // configure EPWM settings

    while(1)
    {
        // In this basic example, we will implement the controller in the main function
        if (duty <= 0.5){
            duty = 0.5;
        } else if (duty >= 0.75){
            duty = 0.75;
        }

        duty_cmp = EPWM_TBPRD * duty;
        EPwm1Regs.CMPA.bit.CMPA = duty_cmp;

        EPwm1Regs.DBRED.bit.DBRED = deadtime_rise;
        EPwm1Regs.DBFED.bit.DBFED = deadtime_fall;

        // ADC read and conversion
        adc_raw_vout = AdcaResultRegs.ADCRESULT0;
        adc_vout = ((float)adc_raw_vout / 4095.0) * 3.0 * 11; // float from 12-bit value to 3V
        // adc_vin = 0.0007 * adc_raw + 0.002;
        adc_raw_iout = AdccResultRegs.ADCRESULT0;
//         adc_iout = ((float)adc_raw_iout * 0.006189 - 10.6);
        adc_iout = ((float)adc_raw_iout * 0.0059 - 10.0928);




        DELAY_US(1000); // Insert a delay longer than the switching period to ensure that the duty ratio
                        //   is updated at most once per switching period (we are implementing single-update PWM)
    }
    return 0;

}
