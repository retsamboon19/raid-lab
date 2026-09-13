"""GPU candidate exploration. Scores are search heuristics, never reported as DPS."""
from array import array
from functools import lru_cache
from pathlib import Path
import heapq
import math
import sys
import time

@lru_cache(maxsize=1)
def _adapters():
    runtime=Path(__file__).parent/'.gpu-runtime'
    if str(runtime) not in sys.path:sys.path.insert(0,str(runtime))
    import wgpu
    return [a for a in wgpu.gpu.enumerate_adapters_sync() if a.info.get('adapter_type') in ('DiscreteGPU','IntegratedGPU')]

def _identifier(adapter,index):
    i=adapter.info
    return f"{i.get('vendor_id')}:{i.get('device_id')}:{i.get('backend_type')}:{index}"

def device_info(selected='auto'):
    try:
        adapters=_adapters()
        if not adapters:raise RuntimeError('No supported hardware GPU detected.')
        devices=[{'id':_identifier(a,i),'name':a.info.get('device'),'backend':a.info.get('backend_type'),'type':a.info.get('adapter_type')} for i,a in enumerate(adapters)]
        chosen=next((d for d in devices if d['id']==selected),None) if selected!='auto' else next((d for d in devices if d['type']=='DiscreteGPU'),devices[0])
        if chosen is None:raise RuntimeError('The selected GPU is no longer available. Choose a detected GPU or Automatic.')
        return {'available':True,**chosen,'devices':devices}
    except Exception as e:return {'available':False,'reason':str(e),'devices':[]}

@lru_cache(maxsize=8)
def _device(identifier):
    return next(a for i,a in enumerate(_adapters()) if _identifier(a,i)==identifier).request_device_sync()

def _dispatch(identifier,inputs,count,length,shader):
    import wgpu
    device=_device(identifier)
    buffers={i:device.create_buffer_with_data(data=data,usage=wgpu.BufferUsage.STORAGE) for i,data in inputs.items()}
    buffers[2]=device.create_buffer(size=count*length*4,usage=wgpu.BufferUsage.STORAGE|wgpu.BufferUsage.COPY_SRC)
    buffers[3]=device.create_buffer(size=count*4,usage=wgpu.BufferUsage.STORAGE|wgpu.BufferUsage.COPY_SRC)
    try:
        module=device.create_shader_module(code=shader)
        pipeline=device.create_compute_pipeline(layout='auto',compute={'module':module,'entry_point':'main'})
        group=device.create_bind_group(layout=pipeline.get_bind_group_layout(0),entries=[{'binding':i,'resource':{'buffer':buf,'offset':0,'size':buf.size}} for i,buf in buffers.items()])
        encoder=device.create_command_encoder();compute=encoder.begin_compute_pass()
        compute.set_pipeline(pipeline);compute.set_bind_group(0,group);compute.dispatch_workgroups((count+63)//64);compute.end()
        device.queue.submit([encoder.finish()])
        return {2:device.queue.read_buffer(buffers[2]).cast('I'),3:device.queue.read_buffer(buffers[3]).cast('f')}
    finally:
        for buffer in buffers.values():buffer.destroy()

def explore(ids,weights,catalog,settings,valid,ordered,count=8192):
    info=device_info(settings.get('gpu_device','auto'))
    if not info['available']:raise ValueError('GPU mode is unavailable: '+info['reason']+'. Choose CPU.')
    started=time.perf_counter();teams=settings['teams'];length=teams*5
    required=0
    g=settings['encounter'].get('guidance',{}) if settings.get('survival_policy')=='guide' else {}
    if settings['cdr']:required|=16
    if settings['healing'] or 'Healing' in g.get('required_tags',[]):required|=32
    if 'Shield' in g.get('required_tags',[]):required|=64
    barrier=settings['encounter'].get('barrier_element')
    if barrier:required|=128
    if settings['element']!='Any':required|=256
    flags=[]
    for n in ids:
        c=catalog[n];f=int(c['burst']) if c['burst'] in ('1','2','3') else 0
        for tag,bit in [('CDR',16),('Healing',32),('Shield',64)]:
            if tag in c['tags']:f|=bit
        if barrier in c['barrier_elements']:f|=128
        # Match CPU eligibility across every class and burst stage. The CPU
        # simulation subsequently checks substantial elemental damage.
        if settings['element'] in c['barrier_elements']:f|=256
        flags.append(f)
    # Each GPU invocation proposes a disjoint roster allocation. Fixed seed is reproducible.
    shader='''
@group(0) @binding(0) var<storage,read> weights:array<f32>;
@group(0) @binding(1) var<storage,read> flags:array<u32>;
@group(0) @binding(2) var<storage,read_write> chosen:array<u32>;
@group(0) @binding(3) var<storage,read_write> scores:array<f32>;
fn hash(x:u32)->u32 {var v=x;v=(v^(v>>16u))*2146121005u;v=(v^(v>>15u))*2221713035u;return v^(v>>16u);}
@compute @workgroup_size(64) fn main(@builtin(global_invocation_id) gid:vec3<u32>) {
 let p=gid.x;if(p>=COUNTu){return;}
 var used:array<u32,25>;var score=0.0;var covered=0u;var teamScore=0.0;
 for(var slot=0u;slot<LENGTHu;slot++){
  let position=slot%5u;var stage=0u;
  if(position==0u){stage=1u;}else if(position==1u){stage=2u;}else if(position<4u){stage=3u;}
  var best=-1e30;var winner=9999u;
  for(var u=0u;u<UNITSu;u++){
   if(stage!=0u && (flags[u]&3u)!=stage){continue;}
   var duplicate=false;for(var prev=0u;prev<slot;prev++){if(used[prev]==u){duplicate=true;}}
   if(duplicate){continue;}
   if(position==4u && ((covered|flags[u])&REQUIREDu)!=REQUIREDu){continue;}
   let rnd=(f32(hash(p*1664525u+slot*1013904223u+u*747796405u+42u)%16777214u)+1.0)/16777216.0;
   let bias=select(0.0,1.4,((flags[u]&REQUIREDu)&~covered)!=0u);
   let value=log(max(weights[u],1.0))-0.9*log(-log(rnd))+bias;
   if(value>best){best=value;winner=u;}
  }
  if(winner==9999u){scores[p]=-1.0;return;}
  used[slot]=winner;chosen[p*LENGTHu+slot]=winner;covered|=flags[winner];teamScore+=weights[winner];
  if(position==4u){score+=teamScore*select(1.0,1.25,(covered&16u)!=0u);covered=0u;teamScore=0.0;}
 }
 scores[p]=score;
}'''
    for key,value in [('COUNT',count),('LENGTH',length),('UNITS',len(ids)),('REQUIRED',required)]:shader=shader.replace(key,str(value))
    result=_dispatch(info['id'],{0:array('f',[weights[n] for n in ids]),1:array('I',flags)},count,length,shader)
    indices=result[2];scores=result[3];plans={}
    for index in heapq.nlargest(min(count,512),range(count),key=lambda x:scores[x]):
        if scores[index]<0:continue
        row=[ids[indices[index*length+j]] for j in range(length)]
        allocation=[ordered(row[i:i+5]) for i in range(0,length,5)]
        if len(set(row))!=length or not all(valid(t,settings) for t in allocation):continue
        key=tuple(sorted(tuple(t) for t in allocation))
        plans[key]=float(scores[index])
    return plans,{'gpu_used':True,'device':info['name'],'gpu_backend':info['backend'],
                  'gpu_proposals':count,'gpu_seconds':round(time.perf_counter()-started,3),
                  'gpu_stage':'Candidate exploration; full combat verification uses CPU workers.'}
