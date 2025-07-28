// NO sweeping, only perturbulation
// Set stop_search = 1, you can stop searching

// Measure var. MPPT_power, MPPT_duty, flag_perturb

 #include "F28x_Project.h" // this includes all headers needed to interact with peripherals (ADC, EPWM, etc.)
 #include "cpu1_init.h"

 // #define ADC_VREF 3.0
 // #define ADC_MAX 4095.0  // 12-bit ADC max value

 volatile Uint16 adc_raw_vout; // 0->4095
 volatile Uint16 adc_raw_iout;
 volatile float adc_vout; // 0->3
 volatile float adc_iout; // 0->3

 volatile Uint16 duty_cmp = EPWM_CMP_INIT;
 volatile float duty = 0.55;

 volatile Uint16 deadtime_rise = EPWM_DEADTIME;
 volatile Uint16 deadtime_fall = EPWM_DEADTIME;


 //Simple Perturb and Observe Algorithm

float MPP_power = 0; //Maximum power point power
float MPP_Duty, MPP_Vin; //Maximum power point duty cycle and input voltage

float duty_step = .005f; //Duty cycle step size
// float duty = 0.5f; //Start MPPT Search at the largest panel voltage of 24V
float duty_max = 0.75f; //Maximum duty cycle to search over
uint32_t wait_time = 10e3; //amount of time to wait after duty cycle update [us]

float iout, vout, pout, iin, vin, pin, eff;

volatile int stop_search = 1; //Flag to stop searching for MPPT
volatile int Perturb_Observe = 0; //Flag to enable perturb and observe
float duty_inc, duty_dec; // For perturbs
volatile int flag_D_inc = 0; // Flag to duty increase
volatile int flag_D_dec = 0; // Flag to duty decrease
volatile int flag_perturb = 0; // Flag to sweep duty

int main(void)
{
    InitSysCtrl(); // Initialize SYSCTL (PLL, Watchdog, etc.)

#ifdef LAUNCHPAD // include this define in project settings if using a LaunchPad
    EALLOW;
    ClkCfgRegs.PERCLKDIVSEL.bit.EPWMCLKDIV = 0; // remove /2 clock division for LaunchPad to make calculations consistent with ControlCard
    EDIS;
#endif

    InitGpio(); // Initialize GPIO register states

    configure_GPIO(); // configure GPIO settings

    DINT;         // Disable ST1.INTM
    IER = 0x0000; // Disable CPU interrupts
    IFR = 0x0000; // Clear all CPU interrupt flags

    InitPieCtrl();      // Initialize PIE control registers
    InitPieVectTable(); // Initialize PIE vector table to default ISR locations...
                        // This will typically be overwritten later

    configure_ADC();  // configure ADC settings
    configure_EPWM(); // configure EPWM settings

    while (1) // main circuit setup
    {
        // 2 Mode ctrl:
        // For safety concern...
        if (duty <= 0.55)
        {
            duty = 0.55;
        }
        else if (duty >= 0.75)
        {
            duty = 0.75;
        }
        // Refresh duty&duty_cmp
        duty_cmp = EPWM_TBPRD * duty;
        EPwm1Regs.CMPA.bit.CMPA = duty_cmp;

        EPwm1Regs.DBRED.bit.DBRED = deadtime_rise;
        EPwm1Regs.DBFED.bit.DBFED = deadtime_fall;

        // ADC read and conversion
        adc_raw_vout = AdcaResultRegs.ADCRESULT0;
        adc_vout = ((float)adc_raw_vout / 4095.0) * 3.0 * 11; // float from 12-bit value to 3V

        adc_raw_iout = AdccResultRegs.ADCRESULT0;
        adc_iout = ((float)adc_raw_iout * 0.006189 - 10.7);

        DELAY_US(100000); // Insert a delay longer than the switching period to ensure that the duty ratio
                        //   is updated at most once per switching period (we are implementing single-update PWM)

        if (!flag_perturb){
            stop_search = 1;
            Perturb_Observe = 0;
        }

        if (!stop_search && flag_perturb)
        {
            //Sweep over the entire duty cycle range to find the maximum power point
            //Wait some time to allow the system to settle
            DELAY_US(wait_time);
            //TODO: Measure Output Power
            pout = adc_iout * adc_vout;
            //update maximum power point
            if (pout > MPP_power){
                MPP_Duty = duty;
                MPP_power = pout;
                MPP_Vin = vin;
            }
            //finished search, return to MPP
            if (duty >= duty_max){
                duty = MPP_Duty;
                stop_search = 1;
                Perturb_Observe = 1;
            }
            //Continue to search for MPP
            else{
                duty += duty_step;
            }
        }

        // Perturb Observe: give a perturb to see changes
        else if(Perturb_Observe && flag_perturb){
            //TODO: Implement Perturb and Observe Algorithm
            //The perturb and observe algorithm first _perturbs_ the current operating point (via a change in duty cycle) and _observes_ if the perturbation yielded an increase or decrease in output power
            //First measure the current output power and compare it to the previously measured output power
            //If the current power is higher than the previous power, and the current duty cycle is larger than the previous duty cycle, make another increase in duty cycle
            //The algorithm should handle both cases where the maximum power requires an increase or decrease in duty cycle
            //Your controller should be able to continually find the maximum power point of the PV panel (even if the incoming solar power changes)

            // Refresh duty&duty_cmp ***current is MPPT***
            duty = MPP_Duty;
            duty_cmp = EPWM_TBPRD * duty;
            EPwm1Regs.CMPA.bit.CMPA = duty_cmp;
            DELAY_US(100000);

            adc_raw_vout = AdcaResultRegs.ADCRESULT0;
            adc_vout = ((float)adc_raw_vout / 4095.0) * 3.0 * 11; // float from 12-bit value to 3V
    
            adc_raw_iout = AdccResultRegs.ADCRESULT0;
            adc_iout = ((float)adc_raw_iout * 0.006189 - 10.7);
            
            MPP_power = adc_iout * adc_vout; // Set current status as MPPT ****

            duty_inc = MPP_Duty + duty_step;
            duty_dec = MPP_Duty - duty_step;
            // Test duty up and down -- Always down, up, down, up...
            if (flag_D_dec == 0 && flag_D_inc == 0){
                duty = duty_dec;
                flag_D_dec = 1;
            }
            if (flag_D_dec == 1 && flag_D_inc == 0){
                duty = duty_inc;
                flag_D_inc = 1;
            }
            if (flag_D_dec == 1 && flag_D_inc == 1){
                flag_D_dec = 0;
                flag_D_inc = 0;
            }

            // Refresh duty&duty_cmp
            duty_cmp = EPWM_TBPRD * duty;
            EPwm1Regs.CMPA.bit.CMPA = duty_cmp;

            DELAY_US(100000);

            adc_raw_vout = AdcaResultRegs.ADCRESULT0;
            adc_vout = ((float)adc_raw_vout / 4095.0) * 3.0 * 11; // float from 12-bit value to 3V
    
            adc_raw_iout = AdccResultRegs.ADCRESULT0;
            adc_iout = ((float)adc_raw_iout * 0.006189 - 10.7);

            // Determine the max power + refresh
            pout = adc_iout * adc_vout;
            if (pout > MPP_power){
                MPP_power = pout;
                MPP_Duty = duty;
            }
        }
        //Add code to update EPWM register
    }
}

