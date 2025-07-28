//Simple Perturb and Observe Algorithm

float MPP_power = 0; //Maximum power point power
float MPP_Duty, MPP_Vin; //Maximum power point duty cycle and input voltage

float duty_step = .005f; //Duty cycle step size
float duty = 0.5f; //Start MPPT Search at the largest panel voltage of 24V
float duty_max = 0.75f; //Maximum duty cycle to search over
uint32_t wait_time = 10e3; //amount of time to wait after duty cycle update [us]

float iout, vout, pout, iin, vin, pin, eff;
uint32_t adc_iout, adc_vout, adc_iin, adc_vin; //Raw ADC values
float iout_gain, vout_gain, iin_gain, vin_gain;
volatile int stop_search = 0; //Flag to stop searching for MPPT
volatile int Perturb_Observe = 0; //Flag to enable perturb and observe

int main(void){
    while(1){
        if (!stop_search){
            //Sweep over the entire duty cycle range to find the maximum power point
            //Wait some time to allow the system to settle
            DELAY_US(wait_time); 
            //TODO: Measure Output Power
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
            }
            //Continue to search for MPP
            else{
                duty += duty_step;
            }
        }
        else if(Perturb_Observe){
            //TODO: Implement Perturb and Observe Algorithm
            //The perturb and observe algorithm first _perturbs_ the current operating point (via a change in duty cycle) and _observes_ if the perturbation yielded an increase or decrease in output power
            //First measure the current output power and compare it to the previously measured output power 
            //If the current power is higher than the previous power, and the current duty cycle is larger than the previous duty cycle, make another increase in duty cycle
            //The algorithm should handle both cases where the maximum power requires an increase or decrease in duty cycle
            //Your controller should be able to continually find the maximum power point of the PV panel (even if the incoming solar power changes)

            
        }
        //Add code to update EPWM register
    }
    return 0;
}
