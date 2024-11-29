This contains the documentation for code updates made to srsRAN Project to support EdgeRIC APIs
## Protobufs
The protobuf schemas/ message formats can be found in ``lib/protobufs/`` folder
> - RT-E2 Report Message -> metrics.proto
> - RT-E2 Policy Message : MCS -> control_mcs.proto
> - RT-E2 Policy Message : DL Scheduling -> control_scheduling.proto

## RT Agent in RAN
Where is it implemented?  
The RT agent is implemented in ``lib/edgeric/``, it consists of the following as ``edgeric`` class    
> - the C compiled protobuf schemas of the RT-E2 Report (metrics.pb.cc)  
> - the C compiled protobuf schemas of the RT-E2 Policy: (control_weights.pb.cc->controls the scheduling decisions) and (control_mcs.pb.cc -> controls the MCS decisions)
> - edgeric.cc -> the RT agent is implemneted as the ``edgeric`` class

## TTI Boundaries
File under concern: ``/lib/scheduler/cell_scheduler.cpp``  
The function run_slot marks the TTI boundaries -
> Start of TTI - set the TTI number  
> Start of TTI - recieve the actions from EdgeRIC - these will be used for the current TTI  
> End of TTI - send the KPIs of this TTI to EdgeRIC

```bash
void cell_scheduler::run_slot(slot_point sl_tx)
{
  // Mark the start of the slot.
  auto slot_start_tp = std::chrono::high_resolution_clock::now();
  //Ushasi 
  tti_counter = tti_counter + 1;
  edgeric::setTTI(tti_counter);   ///// Set the TTI number
  edgeric::get_weights_from_er(); ///// Receive from EdgeRIC
  edgeric::get_mcs_from_er();
  ....
  ....
  // > Schedule UE DL and UL data.
  ue_sched.run_slot(sl_tx, cell_cfg.cell_index);
  
  //
  edgeric::printmyvariables();
  edgeric::send_to_er();         ///// Send to EdgeRIC
  // > Mark stop of the slot processing
  auto slot_stop_tp = std::chrono::high_resolution_clock::now();
  auto slot_dur     = std::chrono::duration_cast<std::chrono::microseconds>(slot_stop_tp - slot_start_tp);
  ......
} 
```
## Scheduling Decisions - Workflow
File to implement the scheduling decision: ``lib/scheduler/ue_scheduling/ue_cell_grid_allocator.cpp`` -> ``edgeric::get_weights``  
Weight based control of resource allocations per UE (rnti):  
```bash
uint16_t rnti = static_cast<uint16_t>(ue_cc->rnti());
      std::optional<float> opt_weights_recvd = edgeric::get_weights(rnti);
      weights_to_log = opt_weights_recvd.has_value() ? opt_weights_recvd.value() : 0.0f;

      if (opt_weights_recvd.has_value()) {
          float weights_recvd = opt_weights_recvd.value();
          // mcs_prbs.n_prbs = weights_recvd *  bwp_dl_cmn.generic_params.crbs.length(); 
          mcs_prbs.n_prbs = weights_recvd * this_tti_unused_crbs;
          mcs_prbs.n_prbs = std::min(mcs_prbs.n_prbs, static_cast<unsigned int>(calc_prbs));
          // Apply expert-configured limits.
          mcs_prbs.n_prbs = std::max(mcs_prbs.n_prbs, expert_cfg.pdsch_nof_rbs.start());
          mcs_prbs.n_prbs = std::min(mcs_prbs.n_prbs, expert_cfg.pdsch_nof_rbs.stop());
      }
```

## MCS Decisions - Workflow
File to implement the scheduling decision: ``lib/scheduler/ue_scheduling/ue_cell_grid_allocator.cpp`` -> ``edgeric::get_mcs``  
MCS decision received per UE (rnti)  
```bash
uint16_t rnti = static_cast<unsigned int>(ue_cc->rnti());
    std::optional<uint8_t> opt_mcs_recvd = edgeric::get_mcs(rnti);

    if (opt_mcs_recvd.has_value()) {
        uint8_t mcs_recvd = opt_mcs_recvd.value();
        mcs_prbs.mcs = mcs_recvd;
    }
```
## Collecting Realtime KPIs
1. **CQI and SNR** -> ``lib/scheduler/policy/scheduler_time_pf.cc``, function calls: ``edgeric::set_snr()`` and ``edgeric::set_cqi()``
2. **UL and DL Buffer** - New pending data (new Tx bytes) -> ``lib/scheduler/policy/scheduler_time_pf.cc``, function calls: ``edgeric::set_ul_buffer()`` and ``edgeric::set_dl_buffer()``
3. **DL tbs** - amount of bytes actually scheduled to be sent in that TTI - may not be actually sent -> ``lib/scheduler/ue_scheduling/ue_cell_grid_allocator.cpp``, function call: ``edgeric::set_dl_tbs()``
4. **UL and DL sent bytes** - the amount of bytes successfully acked in this TTI - representative of system goodput -> ``lib/scheduler/ue_scheduling/ue_event_manager.cpp``, function calls: ``edgeric::set_rx_bytes()`` and ``edgeric::set_tx_bytes()``

**Note** In this codebase, the csi_rs periodicity is 20ms at best, so we get CSI reports from UE every TTI - intermediate ones need to be estimated    
