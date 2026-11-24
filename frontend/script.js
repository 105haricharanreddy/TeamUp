
const API = "/api";
const token = () => localStorage.getItem("teamUpToken") || "";
const user = () => { try { return JSON.parse(localStorage.getItem("teamUpLoggedInUser") || "null"); } catch { return null; } };
async function api(path, options={}) {
  const headers = {"Content-Type":"application/json", ...(options.headers||{})};
  if (token()) headers.Authorization = "Bearer " + token();
  const response = await fetch(API+path,{...options,headers});
  const data = await response.json().catch(()=>({}));
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}
function message(id,text){const el=document.getElementById(id);if(el)el.textContent=text;}
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function logout(){localStorage.removeItem("teamUpToken");localStorage.removeItem("teamUpLoggedInUser");location.href="login.html";}
window.logout=logout;
function requireLogin(){if(!token()){location.href="login.html";return false;}return true;}
function setupAuth(){
 const rf=document.getElementById("registerForm");
 if(rf && document.getElementById("studentName")){
  rf.addEventListener("submit",async e=>{e.preventDefault();message("registerMessage","Creating account...");
   try{const d=await api("/auth/register",{method:"POST",body:JSON.stringify({name:studentName.value.trim(),email:studentEmail.value.trim(),password:studentPassword.value})});
    localStorage.setItem("teamUpToken",d.token);localStorage.setItem("teamUpLoggedInUser",JSON.stringify(d.user));message("registerMessage","Account created. Welcome to TeamUp!");setTimeout(()=>location.href="index.html",700);
   }catch(err){message("registerMessage",err.message);}
  });
 }
 const lf=document.getElementById("loginForm");
 if(lf)lf.addEventListener("submit",async e=>{e.preventDefault();message("loginMessage","Signing in...");
  try{const d=await api("/auth/login",{method:"POST",body:JSON.stringify({email:loginEmail.value.trim(),password:loginPassword.value})});
   localStorage.setItem("teamUpToken",d.token);localStorage.setItem("teamUpLoggedInUser",JSON.stringify(d.user));location.href="index.html";
  }catch(err){message("loginMessage",err.message);}
 });
}
async function loadProjects(){
 const area=document.getElementById("projectList");if(!area)return;
 try{
  const projects=await api("/projects");const q=(document.getElementById("searchInput")?.value||"").toLowerCase();
  const skill=(document.getElementById("skillFilter")?.value||"").toLowerCase();
  const filtered=projects.filter(p=>(p.name+" "+p.description+" "+p.skills.join(" ")).toLowerCase().includes(q)&&(!skill||p.skills.some(s=>s.toLowerCase()===skill)));
  area.innerHTML=filtered.length?filtered.map(p=>`<article class="card"><h3>${esc(p.name)}</h3><p>${esc(p.description)}</p><p>Owner: ${esc(p.owner)}</p><p>Maximum team size: ${p.team_size}</p><p>Required skills: ${p.skills.map(esc).join(", ")}</p><a class="btn" href="details.html?id=${p.id}">View Details</a></article>`).join(""):"<p>No projects found. Try another search.</p>";
  message("filterResult",`Showing ${filtered.length} of ${projects.length} projects`);
 }catch(e){area.textContent=e.message;}
}
function setupProjectPage(){
 const form=document.getElementById("projectForm");
 const ownerField=document.getElementById("projectOwner");
 if(ownerField){ownerField.value=user()?.name||"";ownerField.readOnly=true;}
 if(form)form.addEventListener("submit",async e=>{e.preventDefault();if(!requireLogin())return;message("projectMessage","Creating project...");
  try{await api("/projects",{method:"POST",body:JSON.stringify({name:projectName.value.trim(),description:projectDescription.value.trim(),team_size:Number(teamSize.value),skills:projectSkills.value.trim()})});form.reset();teamSize.value=4;message("projectMessage","Project created successfully!");loadProjects();}
  catch(err){message("projectMessage",err.message);}
 });
 ["searchInput","skillFilter"].forEach(id=>document.getElementById(id)?.addEventListener(id==="searchInput"?"input":"change",loadProjects));
 document.getElementById("clearFilters")?.addEventListener("click",()=>{searchInput.value="";skillFilter.value="";loadProjects();});
 loadProjects();
}
async function setupDetails(){
 const area=document.getElementById("projectDetails");if(!area)return;
 const id=new URLSearchParams(location.search).get("id");if(!id){area.textContent="Project not found.";return;}
 try{const p=await api("/projects/"+id);
  area.innerHTML=`<p class="project-label">PROJECT DETAILS</p><h1>${esc(p.name)}</h1><p>${esc(p.description)}</p><p><b>Project owner:</b> ${esc(p.owner)}</p><p><b>Team size:</b> ${p.team_size}</p><p><b>Skills:</b> ${p.skills.map(esc).join(", ")}</p><button id="joinProjectButton">Request to Join</button><p id="detailMessage"></p>`;
  document.getElementById("joinProjectButton").addEventListener("click",async()=>{try{await api(`/projects/${id}/join`,{method:"POST"});message("detailMessage","Join request sent successfully.");}catch(e){message("detailMessage",e.message);}});
 }catch(e){area.textContent=e.message;}
}
async function setupProfile(){
 const form=document.getElementById("profileForm");if(!form)return;if(!requireLogin())return;
 try{const p=await api("/profile");for(const [id,key] of Object.entries({profileCollege:"college",profileDepartment:"department",profileYear:"year",profileSkills:"skills",profileInterests:"interests",profileBio:"bio"})){const el=document.getElementById(id);if(el)el.value=p[key]||"";}
 const name=document.getElementById("profileName");if(name)name.value=user()?.name||"";
 if(p.college)show(p);
 }catch(e){message("profileMessage",e.message);}
 function show(p){const area=document.getElementById("savedProfile"),display=document.getElementById("profileDisplay");if(!display)return;
 display.innerHTML=[["Name",user()?.name],["College",p.college],["Department",p.department],["Year",p.year],["Skills",p.skills],["Interests",p.interests],["About Me",p.bio]].map(([k,v])=>`<p><b>${k}:</b> ${esc(v)}</p>`).join("");if(area)area.hidden=false;}
 form.addEventListener("submit",async e=>{e.preventDefault();try{const body={college:profileCollege.value.trim(),department:profileDepartment.value,year:profileYear.value,skills:profileSkills.value.trim(),interests:profileInterests.value.trim(),bio:profileBio.value.trim()};await api("/profile",{method:"PUT",body:JSON.stringify(body)});show(body);message("profileMessage","Profile saved successfully!");}catch(e){message("profileMessage",e.message);}});
 document.getElementById("editProfileButton")?.addEventListener("click",()=>{document.getElementById("savedProfile").hidden=true;});
}
async function setupStudents(){
 const area=document.getElementById("studentList");if(!area)return;if(!requireLogin())return;
 let students=[];try{students=await api("/students");}catch(e){area.textContent=e.message;return;}
 const render=()=>{const q=(studentSearch.value||"").toLowerCase(),sk=(studentSkill.value||"").toLowerCase();
 const rows=students.filter(s=>([s.name,s.college,s.department,s.skills,s.interests,s.bio].join(" ").toLowerCase().includes(q))&&(!sk||s.skills.toLowerCase().split(",").map(x=>x.trim()).includes(sk)));
 area.innerHTML=rows.length?rows.map(s=>`<article class="student-card"><h2>${esc(s.name)}</h2><p>College: ${esc(s.college)}</p><p>Department: ${esc(s.department)}</p><p>Year: ${esc(s.year)}</p><p>Skills: ${esc(s.skills)}</p><p>Interests: ${esc(s.interests)}</p><p>${esc(s.bio)}</p><button data-student="${s.id}">Connect</button></article>`).join(""):"<p>No students match your search.</p>";
 message("studentCount",`Showing ${rows.length} of ${students.length} students`);
 area.querySelectorAll("button[data-student]").forEach(b=>b.addEventListener("click",async()=>{try{await api(`/connections/${b.dataset.student}`,{method:"POST"});b.textContent="Request Sent";b.disabled=true;}catch(e){alert(e.message);}}));
 };
 studentSearch?.addEventListener("input",render);studentSkill?.addEventListener("change",render);studentClear?.addEventListener("click",()=>{studentSearch.value="";studentSkill.value="";render();});render();
}
async function setupTeams(){
 const a=document.getElementById("myProjects"),b=document.getElementById("myRequests"),c=document.getElementById("createdProjects"),d=document.getElementById("requestedProjects");
 if(!a&&!b&&!c&&!d)return;if(!requireLogin())return;
 try{const work=await api("/my-work");const projects=work.created.map(p=>`<article class="card"><h3>${esc(p.name)}</h3><p>${esc(p.description)}</p><p>Join requests: ${p.requests.length}</p>${p.requests.map(r=>`<p>${esc(r.name)} — ${esc(r.status)} ${r.status==="Pending"?`<button data-request="${r.id}" data-status="Accepted">Accept</button> <button data-request="${r.id}" data-status="Rejected">Reject</button>`:""}</p>`).join("")}<a href="details.html?id=${p.id}">View Details</a></article>`).join("")||"<p>You haven't created any projects.</p>";
 const requests=work.requested.map(r=>`<article class="card"><h3>${esc(r.name)}</h3><p>Request status: ${esc(r.status)}</p></article>`).join("")||"<p>You haven't sent any join requests.</p>";
 [a,c].filter(Boolean).forEach(x=>x.innerHTML=projects);[b,d].filter(Boolean).forEach(x=>x.innerHTML=requests);
 document.querySelectorAll("button[data-request]").forEach(btn=>btn.addEventListener("click",async()=>{try{await api(`/join-requests/${btn.dataset.request}`,{method:"PATCH",body:JSON.stringify({status:btn.dataset.status})});setupTeams();}catch(e){alert(e.message);}}));
 }catch(e){[a,b,c,d].filter(Boolean).forEach(x=>x.textContent=e.message);}
}
async function setupConnections(){
 const incoming=document.getElementById("connectionRequests"),accepted=document.getElementById("myConnections");if(!incoming||!accepted)return;if(!requireLogin())return;
 try{const data=await api("/connections");incoming.innerHTML=data.incoming.length?data.incoming.map(x=>`<article class="card"><h3>${esc(x.name)}</h3><button data-connection="${x.id}" data-status="Accepted">Accept</button> <button data-connection="${x.id}" data-status="Rejected">Reject</button></article>`).join(""):"<p>No pending connection requests.</p>";
 accepted.innerHTML=data.accepted.length?data.accepted.map(x=>`<article class="card"><h3>${esc(x.name)}</h3><p>Connected</p></article>`).join(""):"<p>You have no accepted connections yet.</p>";
 document.querySelectorAll("button[data-connection]").forEach(btn=>btn.addEventListener("click",async()=>{try{await api(`/connections/${btn.dataset.connection}`,{method:"PATCH",body:JSON.stringify({status:btn.dataset.status})});setupConnections();}catch(e){alert(e.message);}}));
 }catch(e){incoming.textContent=e.message;}
}
function setupWelcome(){const w=document.getElementById("welcomeMessage"),b=document.getElementById("logoutButton");if(w&&user())w.textContent="Welcome, "+user().name+"!";if(b){b.hidden=!token();b.style.display=token()?"inline-block":"none";}}
document.addEventListener("DOMContentLoaded",()=>{setupAuth();setupWelcome();setupProjectPage();setupDetails();setupProfile();setupStudents();setupTeams();setupConnections();});
