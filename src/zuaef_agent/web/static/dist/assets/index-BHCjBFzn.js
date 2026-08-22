(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const o of document.querySelectorAll('link[rel="modulepreload"]'))r(o);new MutationObserver(o=>{for(const n of o)if(n.type==="childList")for(const i of n.addedNodes)i.tagName==="LINK"&&i.rel==="modulepreload"&&r(i)}).observe(document,{childList:!0,subtree:!0});function s(o){const n={};return o.integrity&&(n.integrity=o.integrity),o.referrerPolicy&&(n.referrerPolicy=o.referrerPolicy),o.crossOrigin==="use-credentials"?n.credentials="include":o.crossOrigin==="anonymous"?n.credentials="omit":n.credentials="same-origin",n}function r(o){if(o.ep)return;o.ep=!0;const n=s(o);fetch(o.href,n)}})();const V=globalThis,nt=V.ShadowRoot&&(V.ShadyCSS===void 0||V.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,it=Symbol(),ft=new WeakMap;let Ot=class{constructor(t,s,r){if(this._$cssResult$=!0,r!==it)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=s}get styleSheet(){let t=this.o;const s=this.t;if(nt&&t===void 0){const r=s!==void 0&&s.length===1;r&&(t=ft.get(s)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),r&&ft.set(s,t))}return t}toString(){return this.cssText}};const kt=e=>new Ot(typeof e=="string"?e:e+"",void 0,it),y=(e,...t)=>{const s=e.length===1?e[0]:t.reduce((r,o,n)=>r+(i=>{if(i._$cssResult$===!0)return i.cssText;if(typeof i=="number")return i;throw Error("Value passed to 'css' function must be a 'css' function result: "+i+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(o)+e[n+1],e[0]);return new Ot(s,e,it)},It=(e,t)=>{if(nt)e.adoptedStyleSheets=t.map(s=>s instanceof CSSStyleSheet?s:s.styleSheet);else for(const s of t){const r=document.createElement("style"),o=V.litNonce;o!==void 0&&r.setAttribute("nonce",o),r.textContent=s.cssText,e.appendChild(r)}},$t=nt?e=>e:e=>e instanceof CSSStyleSheet?(t=>{let s="";for(const r of t.cssRules)s+=r.cssText;return kt(s)})(e):e;const{is:Dt,defineProperty:Lt,getOwnPropertyDescriptor:Ht,getOwnPropertyNames:Bt,getOwnPropertySymbols:Ft,getPrototypeOf:qt}=Object,Y=globalThis,vt=Y.trustedTypes,Zt=vt?vt.emptyScript:"",Vt=Y.reactiveElementPolyfillSupport,N=(e,t)=>e,G={toAttribute(e,t){switch(t){case Boolean:e=e?Zt:null;break;case Object:case Array:e=e==null?e:JSON.stringify(e)}return e},fromAttribute(e,t){let s=e;switch(t){case Boolean:s=e!==null;break;case Number:s=e===null?null:Number(e);break;case Object:case Array:try{s=JSON.parse(e)}catch{s=null}}return s}},at=(e,t)=>!Dt(e,t),mt={attribute:!0,type:String,converter:G,reflect:!1,useDefault:!1,hasChanged:at};Symbol.metadata??=Symbol("metadata"),Y.litPropertyMetadata??=new WeakMap;let P=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,s=mt){if(s.state&&(s.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((s=Object.create(s)).wrapped=!0),this.elementProperties.set(t,s),!s.noAccessor){const r=Symbol(),o=this.getPropertyDescriptor(t,r,s);o!==void 0&&Lt(this.prototype,t,o)}}static getPropertyDescriptor(t,s,r){const{get:o,set:n}=Ht(this.prototype,t)??{get(){return this[s]},set(i){this[s]=i}};return{get:o,set(i){const c=o?.call(this);n?.call(this,i),this.requestUpdate(t,c,r)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??mt}static _$Ei(){if(this.hasOwnProperty(N("elementProperties")))return;const t=qt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(N("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(N("properties"))){const s=this.properties,r=[...Bt(s),...Ft(s)];for(const o of r)this.createProperty(o,s[o])}const t=this[Symbol.metadata];if(t!==null){const s=litPropertyMetadata.get(t);if(s!==void 0)for(const[r,o]of s)this.elementProperties.set(r,o)}this._$Eh=new Map;for(const[s,r]of this.elementProperties){const o=this._$Eu(s,r);o!==void 0&&this._$Eh.set(o,s)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const s=[];if(Array.isArray(t)){const r=new Set(t.flat(1/0).reverse());for(const o of r)s.unshift($t(o))}else t!==void 0&&s.push($t(t));return s}static _$Eu(t,s){const r=s.attribute;return r===!1?void 0:typeof r=="string"?r:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,s=this.constructor.elementProperties;for(const r of s.keys())this.hasOwnProperty(r)&&(t.set(r,this[r]),delete this[r]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return It(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,s,r){this._$AK(t,r)}_$ET(t,s){const r=this.constructor.elementProperties.get(t),o=this.constructor._$Eu(t,r);if(o!==void 0&&r.reflect===!0){const n=(r.converter?.toAttribute!==void 0?r.converter:G).toAttribute(s,r.type);this._$Em=t,n==null?this.removeAttribute(o):this.setAttribute(o,n),this._$Em=null}}_$AK(t,s){const r=this.constructor,o=r._$Eh.get(t);if(o!==void 0&&this._$Em!==o){const n=r.getPropertyOptions(o),i=typeof n.converter=="function"?{fromAttribute:n.converter}:n.converter?.fromAttribute!==void 0?n.converter:G;this._$Em=o;const c=i.fromAttribute(s,n.type);this[o]=c??this._$Ej?.get(o)??c,this._$Em=null}}requestUpdate(t,s,r,o=!1,n){if(t!==void 0){const i=this.constructor;if(o===!1&&(n=this[t]),r??=i.getPropertyOptions(t),!((r.hasChanged??at)(n,s)||r.useDefault&&r.reflect&&n===this._$Ej?.get(t)&&!this.hasAttribute(i._$Eu(t,r))))return;this.C(t,s,r)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,s,{useDefault:r,reflect:o,wrapped:n},i){r&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,i??s??this[t]),n!==!0||i!==void 0)||(this._$AL.has(t)||(this.hasUpdated||r||(s=void 0),this._$AL.set(t,s)),o===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(s){Promise.reject(s)}const t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[o,n]of this._$Ep)this[o]=n;this._$Ep=void 0}const r=this.constructor.elementProperties;if(r.size>0)for(const[o,n]of r){const{wrapped:i}=n,c=this[o];i!==!0||this._$AL.has(o)||c===void 0||this.C(o,void 0,n,c)}}let t=!1;const s=this._$AL;try{t=this.shouldUpdate(s),t?(this.willUpdate(s),this._$EO?.forEach(r=>r.hostUpdate?.()),this.update(s)):this._$EM()}catch(r){throw t=!1,this._$EM(),r}t&&this._$AE(s)}willUpdate(t){}_$AE(t){this._$EO?.forEach(s=>s.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(s=>this._$ET(s,this[s])),this._$EM()}updated(t){}firstUpdated(t){}};P.elementStyles=[],P.shadowRootOptions={mode:"open"},P[N("elementProperties")]=new Map,P[N("finalized")]=new Map,Vt?.({ReactiveElement:P}),(Y.reactiveElementVersions??=[]).push("2.1.2");const lt=globalThis,gt=e=>e,J=lt.trustedTypes,_t=J?J.createPolicy("lit-html",{createHTML:e=>e}):void 0,Ct="$lit$",_=`lit$${Math.random().toFixed(9).slice(2)}$`,jt="?"+_,Wt=`<${jt}>`,E=document,M=()=>E.createComment(""),k=e=>e===null||typeof e!="object"&&typeof e!="function",dt=Array.isArray,Gt=e=>dt(e)||typeof e?.[Symbol.iterator]=="function",tt=`[ 	
\f\r]`,U=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,bt=/-->/g,yt=/>/g,z=RegExp(`>|${tt}(?:([^\\s"'>=/]+)(${tt}*=${tt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),xt=/'/g,wt=/"/g,Rt=/^(?:script|style|textarea|title)$/i,Jt=e=>(t,...s)=>({_$litType$:e,strings:t,values:s}),a=Jt(1),O=Symbol.for("lit-noChange"),d=Symbol.for("lit-nothing"),zt=new WeakMap,A=E.createTreeWalker(E,129);function Tt(e,t){if(!dt(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return _t!==void 0?_t.createHTML(t):t}const Kt=(e,t)=>{const s=e.length-1,r=[];let o,n=t===2?"<svg>":t===3?"<math>":"",i=U;for(let c=0;c<s;c++){const l=e[c];let h,f,u=-1,m=0;for(;m<l.length&&(i.lastIndex=m,f=i.exec(l),f!==null);)m=i.lastIndex,i===U?f[1]==="!--"?i=bt:f[1]!==void 0?i=yt:f[2]!==void 0?(Rt.test(f[2])&&(o=RegExp("</"+f[2],"g")),i=z):f[3]!==void 0&&(i=z):i===z?f[0]===">"?(i=o??U,u=-1):f[1]===void 0?u=-2:(u=i.lastIndex-f[2].length,h=f[1],i=f[3]===void 0?z:f[3]==='"'?wt:xt):i===wt||i===xt?i=z:i===bt||i===yt?i=U:(i=z,o=void 0);const g=i===z&&e[c+1].startsWith("/>")?" ":"";n+=i===U?l+Wt:u>=0?(r.push(h),l.slice(0,u)+Ct+l.slice(u)+_+g):l+_+(u===-2?c:g)}return[Tt(e,n+(e[s]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),r]};class I{constructor({strings:t,_$litType$:s},r){let o;this.parts=[];let n=0,i=0;const c=t.length-1,l=this.parts,[h,f]=Kt(t,s);if(this.el=I.createElement(h,r),A.currentNode=this.el.content,s===2||s===3){const u=this.el.content.firstChild;u.replaceWith(...u.childNodes)}for(;(o=A.nextNode())!==null&&l.length<c;){if(o.nodeType===1){if(o.hasAttributes())for(const u of o.getAttributeNames())if(u.endsWith(Ct)){const m=f[i++],g=o.getAttribute(u).split(_),q=/([.?@])?(.*)/.exec(m);l.push({type:1,index:n,name:q[2],strings:g,ctor:q[1]==="."?Qt:q[1]==="?"?Xt:q[1]==="@"?te:Q}),o.removeAttribute(u)}else u.startsWith(_)&&(l.push({type:6,index:n}),o.removeAttribute(u));if(Rt.test(o.tagName)){const u=o.textContent.split(_),m=u.length-1;if(m>0){o.textContent=J?J.emptyScript:"";for(let g=0;g<m;g++)o.append(u[g],M()),A.nextNode(),l.push({type:2,index:++n});o.append(u[m],M())}}}else if(o.nodeType===8)if(o.data===jt)l.push({type:2,index:n});else{let u=-1;for(;(u=o.data.indexOf(_,u+1))!==-1;)l.push({type:7,index:n}),u+=_.length-1}n++}}static createElement(t,s){const r=E.createElement("template");return r.innerHTML=t,r}}function C(e,t,s=e,r){if(t===O)return t;let o=r!==void 0?s._$Co?.[r]:s._$Cl;const n=k(t)?void 0:t._$litDirective$;return o?.constructor!==n&&(o?._$AO?.(!1),n===void 0?o=void 0:(o=new n(e),o._$AT(e,s,r)),r!==void 0?(s._$Co??=[])[r]=o:s._$Cl=o),o!==void 0&&(t=C(e,o._$AS(e,t.values),o,r)),t}class Yt{constructor(t,s){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=s}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:s},parts:r}=this._$AD,o=(t?.creationScope??E).importNode(s,!0);A.currentNode=o;let n=A.nextNode(),i=0,c=0,l=r[0];for(;l!==void 0;){if(i===l.index){let h;l.type===2?h=new B(n,n.nextSibling,this,t):l.type===1?h=new l.ctor(n,l.name,l.strings,this,t):l.type===6&&(h=new ee(n,this,t)),this._$AV.push(h),l=r[++c]}i!==l?.index&&(n=A.nextNode(),i++)}return A.currentNode=E,o}p(t){let s=0;for(const r of this._$AV)r!==void 0&&(r.strings!==void 0?(r._$AI(t,r,s),s+=r.strings.length-2):r._$AI(t[s])),s++}}class B{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,s,r,o){this.type=2,this._$AH=d,this._$AN=void 0,this._$AA=t,this._$AB=s,this._$AM=r,this.options=o,this._$Cv=o?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const s=this._$AM;return s!==void 0&&t?.nodeType===11&&(t=s.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,s=this){t=C(this,t,s),k(t)?t===d||t==null||t===""?(this._$AH!==d&&this._$AR(),this._$AH=d):t!==this._$AH&&t!==O&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Gt(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==d&&k(this._$AH)?this._$AA.nextSibling.data=t:this.T(E.createTextNode(t)),this._$AH=t}$(t){const{values:s,_$litType$:r}=t,o=typeof r=="number"?this._$AC(t):(r.el===void 0&&(r.el=I.createElement(Tt(r.h,r.h[0]),this.options)),r);if(this._$AH?._$AD===o)this._$AH.p(s);else{const n=new Yt(o,this),i=n.u(this.options);n.p(s),this.T(i),this._$AH=n}}_$AC(t){let s=zt.get(t.strings);return s===void 0&&zt.set(t.strings,s=new I(t)),s}k(t){dt(this._$AH)||(this._$AH=[],this._$AR());const s=this._$AH;let r,o=0;for(const n of t)o===s.length?s.push(r=new B(this.O(M()),this.O(M()),this,this.options)):r=s[o],r._$AI(n),o++;o<s.length&&(this._$AR(r&&r._$AB.nextSibling,o),s.length=o)}_$AR(t=this._$AA.nextSibling,s){for(this._$AP?.(!1,!0,s);t!==this._$AB;){const r=gt(t).nextSibling;gt(t).remove(),t=r}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}}class Q{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,s,r,o,n){this.type=1,this._$AH=d,this._$AN=void 0,this.element=t,this.name=s,this._$AM=o,this.options=n,r.length>2||r[0]!==""||r[1]!==""?(this._$AH=Array(r.length-1).fill(new String),this.strings=r):this._$AH=d}_$AI(t,s=this,r,o){const n=this.strings;let i=!1;if(n===void 0)t=C(this,t,s,0),i=!k(t)||t!==this._$AH&&t!==O,i&&(this._$AH=t);else{const c=t;let l,h;for(t=n[0],l=0;l<n.length-1;l++)h=C(this,c[r+l],s,l),h===O&&(h=this._$AH[l]),i||=!k(h)||h!==this._$AH[l],h===d?t=d:t!==d&&(t+=(h??"")+n[l+1]),this._$AH[l]=h}i&&!o&&this.j(t)}j(t){t===d?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class Qt extends Q{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===d?void 0:t}}class Xt extends Q{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==d)}}class te extends Q{constructor(t,s,r,o,n){super(t,s,r,o,n),this.type=5}_$AI(t,s=this){if((t=C(this,t,s,0)??d)===O)return;const r=this._$AH,o=t===d&&r!==d||t.capture!==r.capture||t.once!==r.once||t.passive!==r.passive,n=t!==d&&(r===d||o);o&&this.element.removeEventListener(this.name,this,r),n&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class ee{constructor(t,s,r){this.element=t,this.type=6,this._$AN=void 0,this._$AM=s,this.options=r}get _$AU(){return this._$AM._$AU}_$AI(t){C(this,t)}}const se=lt.litHtmlPolyfillSupport;se?.(I,B),(lt.litHtmlVersions??=[]).push("3.3.3");const re=(e,t,s)=>{const r=s?.renderBefore??t;let o=r._$litPart$;if(o===void 0){const n=s?.renderBefore??null;r._$litPart$=o=new B(t.insertBefore(M(),n),n,void 0,s??{})}return o._$AI(e),o};const ct=globalThis;class $ extends P{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const s=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=re(s,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return O}}$._$litElement$=!0,$.finalized=!0,ct.litElementHydrateSupport?.({LitElement:$});const oe=ct.litElementPolyfillSupport;oe?.({LitElement:$});(ct.litElementVersions??=[]).push("4.2.2");const x=e=>(t,s)=>{s!==void 0?s.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)};const ne={attribute:!0,type:String,converter:G,reflect:!1,hasChanged:at},ie=(e=ne,t,s)=>{const{kind:r,metadata:o}=s;let n=globalThis.litPropertyMetadata.get(o);if(n===void 0&&globalThis.litPropertyMetadata.set(o,n=new Map),r==="setter"&&((e=Object.create(e)).wrapped=!0),n.set(s.name,e),r==="accessor"){const{name:i}=s;return{set(c){const l=t.get.call(this);t.set.call(this,c),this.requestUpdate(i,l,e,!0,c)},init(c){return c!==void 0&&this.C(i,void 0,e,c),c}}}if(r==="setter"){const{name:i}=s;return function(c){const l=this[i];t.call(this,c),this.requestUpdate(i,l,e,!0,c)}}throw Error("Unsupported decorator location: "+r)};function p(e){return(t,s)=>typeof s=="object"?ie(e,t,s):((r,o,n)=>{const i=o.hasOwnProperty(n);return o.constructor.createProperty(n,r),i?Object.getOwnPropertyDescriptor(o,n):void 0})(e,t,s)}function R(e){return p({...e,state:!0,attribute:!1})}class ae extends Error{constructor(t,s,r){super(s),this.code=t,this.status=r}}async function et(e){const t=await fetch(e);if(!t.ok){let s="INTERNAL_ERROR",r=`HTTP ${t.status}`;try{const o=await t.json();o.error?.code&&(s=o.error.code),o.error?.message&&(r=o.error.message)}catch{}throw new ae(s,r,t.status)}return await t.json()}const At=200,st={health:()=>et("/api/health"),listRuns:e=>et(e?`/api/runs?limit=${At}&cursor=${encodeURIComponent(e)}`:`/api/runs?limit=${At}`),getRun:e=>et(`/api/runs/${encodeURIComponent(e)}`)},le={inspectorTab:"summary"},W=864e5;function de(e){if(!e)return"";const t=new Date(e);return Number.isNaN(t.getTime())?"":t.toLocaleTimeString(void 0,{hour12:!1})}function Et(e){if(!e)return"";const t=new Date(e);return Number.isNaN(t.getTime())?"":t.toLocaleString(void 0,{year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:!1})}function ce(e,t=Date.now()){if(!e)return"—";const s=new Date(e);if(Number.isNaN(s.getTime()))return"—";const r=t-s.getTime();return r<6e4?"just now":r<36e5?`${Math.floor(r/6e4)}m ago`:r<W?`${Math.floor(r/36e5)}h ago`:r<7*W?`${Math.floor(r/W)}d ago`:s.toLocaleDateString()}function ot(e){if(e==null||e<0)return"";const t=e/1e3;if(t<60)return`${t.toFixed(1)}s`;const s=Math.floor(t/60),r=Math.round(t-s*60);return`${s}m${String(r).padStart(2,"0")}s`}function St(e){return typeof e!="number"?"":e>=1e3?`${(e/1e3).toFixed(1)}k`:String(e)}function Ut(e){return e==null?"Unknown":e>=1048576?`${(e/1048576).toFixed(1)} MB`:e>=1024?`${(e/1024).toFixed(1)} KB`:`${e} B`}function ue(e){if(!e)return"";const t=[],s=St(e.input_tokens),r=St(e.output_tokens);return s&&t.push(`${s} in`),r&&t.push(`${r} out`),t.join(" · ")}function pe(e,t=Date.now()){if(!e.started_at)return"Older";const s=new Date(e.started_at).getTime();if(Number.isNaN(s))return"Older";const r=new Date(t).setHours(0,0,0,0);return s>=r?"Today":s>=r-W?"Yesterday":"Older"}const Nt={completed:"✓",failed:"✗",paused:"⏸",incomplete:"◔",started:"●",unresolved:"?",unknown:"?",limit_reached:"⏹"};function he(e){return e?Nt[e]??"·":""}function fe(e,t){if(t)return e.find(s=>s.id===t)}var $e=Object.defineProperty,ve=Object.getOwnPropertyDescriptor,ut=(e,t,s,r)=>{for(var o=r>1?void 0:r?ve(t,s):t,n=e.length-1,i;n>=0;n--)(i=e[n])&&(o=(r?i(t,s,o):i(o))||o);return r&&o&&$e(t,s,o),o};let D=class extends ${constructor(){super(...arguments),this.artifacts=[],this.pause=null}render(){return a`
      <span class="label">Artifact</span>
      ${this.artifacts.length===0?a`<span class="none">No artifacts recorded for this run</span>`:this.artifacts.map(e=>a`<span class="artifact" title=${e.sha256}>
              <span class="path">${e.path}</span>
              <span class="fact">${Ut(e.size)}</span>
              <span class="fact">${e.change}</span>
              <span class="fact">sha256:${e.sha256.slice(0,12)}</span>
            </span>`)}
      ${this.pause?a`<span class="pause">
            ⏸ paused — ${this.pause.pending_approvals.length} approval(s) pending
            (supervision not wired in read-only build)
          </span>`:""}
    `}};D.styles=y`
    :host {
      display: flex;
      align-items: center;
      gap: var(--z-space-4);
      padding: var(--z-space-2) var(--z-space-3);
      border-top: 1px solid var(--z-border);
      background: var(--z-surface);
      overflow-x: auto;
      white-space: nowrap;
      flex-shrink: 0;
    }
    .label {
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--z-text-subtle);
      flex-shrink: 0;
    }
    .artifact {
      display: inline-flex;
      align-items: baseline;
      gap: var(--z-space-2);
      font-family: var(--z-font-mono);
      font-size: 12px;
    }
    .path { color: var(--z-text); }
    .fact { color: var(--z-text-muted); font-size: 11px; }
    .none { color: var(--z-text-subtle); font-size: 12px; }
    .pause {
      color: var(--z-warning);
      font-size: 12px;
      border-left: 1px solid var(--z-border);
      padding-left: var(--z-space-4);
      flex-shrink: 0;
    }
  `;ut([p({attribute:!1})],D.prototype,"artifacts",2);ut([p({attribute:!1})],D.prototype,"pause",2);D=ut([x("zuaef-artifact-bar")],D);var me=Object.defineProperty,ge=Object.getOwnPropertyDescriptor,Mt=(e,t,s,r)=>{for(var o=r>1?void 0:r?ge(t,s):t,n=e.length-1,i;n>=0;n--)(i=e[n])&&(o=(r?i(t,s,o):i(o))||o);return r&&o&&me(t,s,o),o};let K=class extends ${constructor(){super(...arguments),this.status=""}render(){const e=this.status||"unknown";return a`<span class=${e}
      ><span aria-hidden="true">${Nt[e]??"·"}</span>${e}</span
    >`}};K.styles=y`
    span {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-family: var(--z-font-mono);
      font-size: 11px;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      white-space: nowrap;
    }
    .completed { color: var(--z-success); }
    .failed { color: var(--z-danger); }
    .paused { color: var(--z-warning); }
    .limit_reached { color: var(--z-warning); }
    .incomplete, .started { color: var(--z-accent); }
    .unknown, .unresolved { color: var(--z-text-muted); }
  `;Mt([p()],K.prototype,"status",2);K=Mt([x("zuaef-status-badge")],K);var _e=Object.defineProperty,be=Object.getOwnPropertyDescriptor,X=(e,t,s,r)=>{for(var o=r>1?void 0:r?be(t,s):t,n=e.length-1,i;n>=0;n--)(i=e[n])&&(o=(r?i(t,s,o):i(o))||o);return r&&o&&_e(t,s,o),o};const Pt=2e3,Z=2e4;let j=class extends ${constructor(){super(...arguments),this.projection=null,this.selectedEventId="",this.inspectorTab="summary"}get row(){return fe(this.projection?.timeline??[],this.selectedEventId)}get availableTabs(){const e=this.row;if(!e)return["summary"];const t=["summary"];return(e.payload.response_parts??[]).length>0&&t.push("io"),e.usage&&Object.keys(e.usage).length>0&&t.push("usage"),t.push("raw"),t}setTab(e){this.dispatchEvent(new CustomEvent("tab-selected",{detail:{tab:e},bubbles:!0,composed:!0}))}render(){const e=this.availableTabs,t=e.includes(this.inspectorTab)?this.inspectorTab:"summary",s=this.row;return a`
      ${e.length>1?a`<div class="tabs" role="tablist">
            ${e.map(r=>a`<button
                role="tab"
                aria-selected=${r===t?"true":"false"}
                @click=${()=>this.setTab(r)}
              >
                ${ye[r]}
              </button>`)}
          </div>`:""}
      <div class="scroll">
        ${s?this.renderEvent(t,s):this.renderRunOverview()}
      </div>
    `}renderEvent(e,t){switch(e){case"io":return this.renderIo(t);case"usage":return this.renderUsage(t);case"raw":return this.renderRaw(t);default:return this.renderSummary(t)}}renderSummary(e){const s=(e.payload.events??[]).find(r=>r.tool_call_id)?.tool_call_id;return a`
      <h3>${e.title}</h3>
      <dl>
        <dt>Status</dt>
        <dd><zuaef-status-badge .status=${e.status??""}></zuaef-status-badge></dd>
        <dt>Kind</dt>
        <dd>${e.kind}</dd>
        ${e.step_index!==null?a`<dt>Step</dt><dd>#${e.step_index}</dd>`:d}
        <dt>Started</dt>
        <dd class=${e.started_at?"":"none"}>${e.started_at??"Unknown"}</dd>
        <dt>Finished</dt>
        <dd class=${e.finished_at?"":"none"}>${e.finished_at??"Unknown"}</dd>
        <dt>Duration</dt>
        <dd class=${e.duration_ms!==null?"":"none"}>
          ${e.duration_ms!==null?ot(e.duration_ms):"Not derivable"}
        </dd>
        ${s?a`<dt>tool_call_id</dt><dd>${String(s)}</dd>`:d}
        ${e.detail?a`<dt>Error</dt><dd class="error-line">${e.detail}</dd>`:d}
        <dt>Derived from</dt>
        <dd>${e.source.join(", ")}</dd>
      </dl>
      ${this.renderEventPayloadHint(e)}
    `}renderEventPayloadHint(e){if(e.kind==="model_request"){const t=(e.payload.response_parts??[]).length>0;return a`<h4>Persisted data</h4>
        <p class="muted">
          ${t?"Per-response output parts are persisted (see Input/Output).":"No response message persisted for this request."}
        </p>`}if(e.kind==="tool_call"){const t=e.detail;return a`<h4>Persisted data</h4>
        <p class="muted">
          ${t?`Effect ledger: ${t}`:"No effect summary recorded."}
          Raw lifecycle events are under Raw.
        </p>`}return d}renderIo(e){const t=e.payload.response_parts??[];return t.length===0?a`<p class="muted">Not persisted</p>`:a`${t.map((s,r)=>this.renderPart(s,r))}`}renderPart(e,t){const s=typeof e.content=="string"?e.content:null;return a`
      <div class="part">
        <h4>Response part #${t} · ${e.part_kind}</h4>
        ${e.tool_name?a`<dl><dt>Tool</dt><dd>${e.tool_name}</dd></dl>`:d}
        ${s!==null?this.renderText(s,e.truncated===!0):d}
        ${e.args?a`<details>
              <summary>args</summary>
              <pre>${JSON.stringify(e.args,null,2)}</pre>
            </details>`:d}
      </div>
    `}renderText(e,t){if(e.length<=Pt)return a`<pre>${e}</pre>`;const s=t||e.length>=Z?" (already truncated by the API)":"";return a`<pre>${e.slice(0,Pt)}…</pre>
    <details>
      <summary>Show full text (${e.length.toLocaleString()} chars)${s}</summary>
      <pre>${e}</pre>
    </details>`}renderUsage(e){const t=e.usage??{};return a`
      <h3>Usage</h3>
      <dl>
        <dt>Input tokens</dt>
        <dd class=${t.input_tokens!==void 0?"":"none"}>
          ${t.input_tokens!==void 0?t.input_tokens.toLocaleString():"Unknown"}
        </dd>
        <dt>Output tokens</dt>
        <dd class=${t.output_tokens!==void 0?"":"none"}>
          ${t.output_tokens!==void 0?t.output_tokens.toLocaleString():"Unknown"}
        </dd>
        ${typeof t.requests=="number"?a`<dt>Requests</dt><dd>${t.requests}</dd>`:d}
      </dl>
    `}renderRaw(e){const t=JSON.stringify(e.payload,null,2)??"{}";return a`
      <h3>Raw</h3>
      <p class="muted">Exactly what GET /api/runs returned for this row.</p>
      ${t.length>Z?a`<p class="muted">Preview truncated at ${Z.toLocaleString()} chars.</p>
            <pre>${t.slice(0,Z)}…</pre>`:a`<pre>${t}</pre>`}
    `}renderRunOverview(){const e=this.projection;if(!e)return a`<p class="muted">Select a run.</p>`;const t=e.run,s=e.composition;return a`
      <h3>${t.display_label}</h3>
      <dl>
        <dt>Status</dt>
        <dd><zuaef-status-badge .status=${t.status}></zuaef-status-badge></dd>
        <dt>Run ID</dt>
        <dd>${t.run_id}</dd>
        ${t.conversation_id?a`<dt>Conversation</dt><dd>${t.conversation_id}</dd>`:d}
        ${t.parent_run_id?a`<dt>Parent run</dt><dd>${t.parent_run_id}</dd>`:d}
        ${t.continued_from_run_id?a`<dt>Continued from</dt><dd>${t.continued_from_run_id}</dd>`:d}
        <dt>Model</dt>
        <dd class=${t.model?"":"none"}>${t.model??"Unknown"}</dd>
        <dt>Profile</dt>
        <dd class=${t.profile?"":"none"}>${t.profile??"Unknown"}</dd>
        ${t.agent_name?a`<dt>Agent</dt><dd>${t.agent_name}</dd>`:d}
        <dt>Started</dt>
        <dd class=${t.started_at?"":"none"}>${Et(t.started_at)||"Unknown"}</dd>
        <dt>Finished</dt>
        <dd class=${t.finished_at?"":"none"}>${Et(t.finished_at)||"Unknown"}</dd>
        <dt>Duration</dt>
        <dd class=${t.duration_ms!==null?"":"none"}>
          ${t.duration_ms!==null?ot(t.duration_ms):"Not derivable"}
        </dd>
        <dt>Requests</dt>
        <dd>${t.request_count}</dd>
        <dt>Tool calls</dt>
        <dd>${t.tool_call_count}</dd>
      </dl>

      <h4>Usage</h4>
      ${e.usage?a`<dl>
            <dt>Input tokens</dt>
            <dd class=${e.usage.input_tokens!==void 0?"":"none"}>
              ${e.usage.input_tokens!==void 0?e.usage.input_tokens.toLocaleString():"Unknown"}
            </dd>
            <dt>Output tokens</dt>
            <dd class=${e.usage.output_tokens!==void 0?"":"none"}>
              ${e.usage.output_tokens!==void 0?e.usage.output_tokens.toLocaleString():"Unknown"}
            </dd>
            <dt>Basis</dt>
            <dd>${e.usage.source??"unknown"}</dd>
          </dl>`:a`<p class="muted">Not persisted</p>`}

      <h4>Composition</h4>
      ${s?a`<details>
            <summary>${s.profile??"composition recorded"}</summary>
            <pre>${JSON.stringify(s,null,2)}</pre>
          </details>`:a`<p class="muted">Receipt unavailable</p>`}

      ${e.pause?a`<h4>Pause</h4>
            <p class="muted">
              Paused with ${e.pause.pending_approvals.length} pending
              approval(s). Supervision actions are not part of this read-only build.
            </p>`:d}

      ${e.unresolved_effects.length>0?a`<h4>Unresolved effects</h4>
            <pre>${JSON.stringify(e.unresolved_effects,null,2)}</pre>`:d}

      ${e.diagnostics.length>0?a`<h4>Diagnostics</h4>
            ${e.diagnostics.map(r=>a`<p class="diag">${r}</p>`)}`:d}

      ${e.artifacts.length>0?a`<h4>Artifacts</h4>
            ${e.artifacts.map(r=>a`<p class="muted">
                ${r.path}${r.size!==null?` — ${Ut(r.size)}`:""}
              </p>`)}`:d}
    `}};j.styles=y`
    :host {
      display: flex;
      flex-direction: column;
      min-height: 0;
      background: var(--z-surface);
      border-left: 1px solid var(--z-border);
    }
    .tabs {
      display: flex;
      border-bottom: 1px solid var(--z-border);
      flex-shrink: 0;
    }
    .tabs button {
      padding: var(--z-space-2) var(--z-space-3);
      font-size: 12px;
      color: var(--z-text-muted);
      border-bottom: 1px solid transparent;
      margin-bottom: -1px;
    }
    .tabs button[aria-selected="true"] {
      color: var(--z-text);
      border-bottom-color: var(--z-accent);
    }
    .scroll {
      flex: 1;
      overflow-y: auto;
      min-height: 0;
      padding: var(--z-space-3);
    }
    h3 {
      margin: 0 0 var(--z-space-2);
      font-size: 13px;
    }
    h4 {
      margin: var(--z-space-4) 0 var(--z-space-1);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--z-text-subtle);
    }
    dl {
      display: grid;
      grid-template-columns: 110px minmax(0, 1fr);
      gap: 3px var(--z-space-2);
      margin: 0;
    }
    dt { color: var(--z-text-muted); font-size: 12px; }
    dd {
      margin: 0;
      font-family: var(--z-font-mono);
      font-size: 12px;
      overflow-wrap: anywhere;
    }
    dd.none { color: var(--z-text-subtle); }
    pre {
      margin: var(--z-space-2) 0;
      padding: var(--z-space-2);
      background: var(--z-bg);
      border: 1px solid var(--z-border);
      border-radius: var(--z-radius);
      font-size: 11px;
      overflow-x: auto;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      max-height: 420px;
      overflow-y: auto;
    }
    details summary {
      cursor: pointer;
      color: var(--z-accent);
      font-size: 12px;
      user-select: none;
    }
    .part {
      border-top: 1px solid var(--z-border);
      padding-top: var(--z-space-2);
      margin-top: var(--z-space-2);
    }
    .part:first-of-type { border-top: none; margin-top: 0; padding-top: 0; }
    .muted { color: var(--z-text-muted); font-size: 12px; }
    .diag {
      color: var(--z-warning);
      font-family: var(--z-font-mono);
      font-size: 11px;
      overflow-wrap: anywhere;
      margin: 2px 0;
    }
    .error-line { color: var(--z-danger); overflow-wrap: anywhere; }
  `;X([p({attribute:!1})],j.prototype,"projection",2);X([p()],j.prototype,"selectedEventId",2);X([p()],j.prototype,"inspectorTab",2);j=X([x("zuaef-inspector")],j);const ye={summary:"Summary",io:"Input/Output",usage:"Usage",raw:"Raw"};var xe=Object.defineProperty,we=Object.getOwnPropertyDescriptor,pt=(e,t,s,r)=>{for(var o=r>1?void 0:r?we(t,s):t,n=e.length-1,i;n>=0;n--)(i=e[n])&&(o=(r?i(t,s,o):i(o))||o);return r&&o&&xe(t,s,o),o};let L=class extends ${constructor(){super(...arguments),this.selected=!1}select(){this.dispatchEvent(new CustomEvent("run-selected",{detail:{runId:this.run.run_id},bubbles:!0,composed:!0}))}render(){const e=this.run,t=[e.model,e.profile].filter(Boolean).join(" · ");return a`
      <button
        role="option"
        aria-selected=${this.selected?"true":"false"}
        title=${`${e.display_label} — ${e.status} (${e.started_at??"unknown start"})`}
        @click=${this.select}
      >
        <span class="glyph ${e.status}" aria-hidden="true"
          >${ze(e.status)}</span
        >
        <span class="label">${e.display_label}</span>
        <span class="time">${ce(e.started_at)}</span>
        ${t?a`<span class="meta">${t}</span>`:a`<span class="meta">no model/profile recorded</span>`}
      </button>
    `}};L.styles=y`
    button {
      display: grid;
      grid-template-columns: 14px minmax(0, 1fr) auto;
      gap: 2px var(--z-space-2);
      width: 100%;
      padding: 5px var(--z-space-3);
      text-align: left;
      border-left: 2px solid transparent;
    }
    button:hover { background: var(--z-surface-hover); }
    button[aria-selected="true"] {
      background: var(--z-surface-hover);
      border-left-color: var(--z-accent);
    }
    .glyph {
      grid-row: 1 / 3;
      align-self: center;
      font-family: var(--z-font-mono);
      font-size: 11px;
    }
    .glyph.completed { color: var(--z-success); }
    .glyph.failed { color: var(--z-danger); }
    .glyph.paused, .glyph.limit_reached { color: var(--z-warning); }
    .glyph.incomplete, .glyph.started { color: var(--z-accent); }
    .label {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--z-text);
    }
    .meta {
      font-size: 11px;
      color: var(--z-text-subtle);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .time {
      grid-column: 3;
      grid-row: 1 / 3;
      align-self: center;
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-text-muted);
    }
  `;pt([p({attribute:!1})],L.prototype,"run",2);pt([p({type:Boolean})],L.prototype,"selected",2);L=pt([x("zuaef-run-row")],L);function ze(e){switch(e){case"completed":return"✓";case"failed":return"✗";case"paused":return"⏸";case"limit_reached":return"⏹";case"incomplete":case"started":return"●";default:return"?"}}var Ae=Object.defineProperty,Ee=Object.getOwnPropertyDescriptor,T=(e,t,s,r)=>{for(var o=r>1?void 0:r?Ee(t,s):t,n=e.length-1,i;n>=0;n--)(i=e[n])&&(o=(r?i(t,s,o):i(o))||o);return r&&o&&Ae(t,s,o),o};let b=class extends ${constructor(){super(...arguments),this.runs=[],this.selectedRunId="",this.nextCursor=null,this.loadingMore=!1,this.filter=""}onFilter(e){this.dispatchEvent(new CustomEvent("run-filter",{detail:{value:e.target.value},bubbles:!0,composed:!0}))}passesFilter(e){return this.filter===""?!0:Se(e,this.filter)}render(){const e=this.runs.filter(o=>this.passesFilter(o)),t=[["Today",[]],["Yesterday",[]],["Older",[]]];for(const o of e)t[["Today","Yesterday","Older"].indexOf(pe(o))][1].push(o);const s=e.length,r=this.runs.length;return a`
      <div class="filter">
        <input
          type="search"
          placeholder="Filter runs…"
          .value=${this.filter}
          @input=${this.onFilter}
          aria-label="Filter runs"
        />
      </div>
      <div class="scroll" role="listbox" aria-label="Runs">
        ${r===0?a`<div class="state">Loading runs…</div>`:s===0?a`<div class="state">No runs match this filter.</div>`:t.map(([o,n])=>n.length>0?a`
                        <div class="group">${o}</div>
                        ${n.map(i=>a`
                            <zuaef-run-row
                              role="option"
                              .run=${i}
                              ?selected=${i.run_id===this.selectedRunId}
                            ></zuaef-run-row>
                          `)}
                      `:"")}
      </div>
      ${this.nextCursor?a`<button
            class="more"
            ?disabled=${this.loadingMore}
            @click=${()=>this.dispatchEvent(new CustomEvent("load-more",{bubbles:!0,composed:!0}))}
          >
            ${this.loadingMore?"Loading…":`Load more (${s} of ${r}+ loaded)`}
          </button>`:a`<div class="count">${s}${s<r?` of ${r}`:""} runs</div>`}
    `}};b.styles=y`
    :host {
      display: flex;
      flex-direction: column;
      min-height: 0;
      background: var(--z-surface);
      border-right: 1px solid var(--z-border);
    }
    .filter {
      padding: var(--z-space-2) var(--z-space-3);
      border-bottom: 1px solid var(--z-border);
    }
    input {
      width: 100%;
      background: var(--z-bg);
      border: 1px solid var(--z-border);
      border-radius: var(--z-radius);
      padding: 3px var(--z-space-2);
      color: var(--z-text);
      font-family: var(--z-font-mono);
      font-size: 12px;
    }
    .scroll {
      flex: 1;
      overflow-y: auto;
      min-height: 0;
    }
    .group {
      padding: var(--z-space-2) var(--z-space-3) var(--z-space-1);
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--z-text-subtle);
    }
    .more,
    .state {
      display: block;
      width: 100%;
      padding: var(--z-space-2) var(--z-space-3);
      border: none;
      border-top: 1px solid var(--z-border);
      color: var(--z-text-muted);
      font-size: 12px;
      text-align: left;
    }
    button.more:hover { background: var(--z-surface-hover); color: var(--z-text); }
    .count {
      padding: var(--z-space-1) var(--z-space-3);
      border-top: 1px solid var(--z-border);
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-text-subtle);
    }
  `;T([p({attribute:!1})],b.prototype,"runs",2);T([p()],b.prototype,"selectedRunId",2);T([p({attribute:!1})],b.prototype,"nextCursor",2);T([p({type:Boolean})],b.prototype,"loadingMore",2);T([p()],b.prototype,"filter",2);b=T([x("zuaef-run-list")],b);function Se(e,t){return[e.display_label,e.run_id,e.model,e.profile,e.status].filter(Boolean).join(`
`).toLowerCase().includes(t.toLowerCase())}var Pe=Object.defineProperty,Oe=Object.getOwnPropertyDescriptor,ht=(e,t,s,r)=>{for(var o=r>1?void 0:r?Oe(t,s):t,n=e.length-1,i;n>=0;n--)(i=e[n])&&(o=(r?i(t,s,o):i(o))||o);return r&&o&&Pe(t,s,o),o};const Ce={run:"RUN",model_request:"REQ",tool_call:"TOOL"};let H=class extends ${constructor(){super(...arguments),this.selected=!1}select(){this.dispatchEvent(new CustomEvent("event-selected",{detail:{rowId:this.row.id},bubbles:!0,composed:!0}))}render(){const e=this.row,t=e.kind==="run",s=Ce[e.kind]??"EVENT",r=a`<span class="summary"
      >${e.title}${e.detail?a` <span class="detail">— ${e.detail}</span>`:""}</span
    >`;return a`
      <button
        role="option"
        aria-selected=${this.selected?"true":"false"}
        class=${e.status?`state-${e.status}`:""}
        title=${e.title}
        @click=${this.select}
      >
        <span class="time">${de(e.started_at)}</span>
        <span class="kind">${t?"":s}</span>
        <span class="step">${e.step_index!==null?`#${e.step_index}`:""}</span>
        ${r}
        <span class="dur">${ot(e.duration_ms)}</span>
        <span class="usage">${ue(e.usage)}</span>
        <span class="status ${e.status??""}"
          >${e.status?`${he(e.status)} ${e.status}`:""}</span
        >
      </button>
    `}};H.styles=y`
    button {
      display: grid;
      grid-template-columns:
        66px 44px 34px minmax(0, 1fr) 62px 110px 92px;
      gap: var(--z-space-3);
      align-items: baseline;
      width: 100%;
      padding: 2px var(--z-space-3);
      font-family: var(--z-font-mono);
      font-size: 12px;
      text-align: left;
      border-left: 2px solid transparent;
      white-space: nowrap;
    }
    button:hover { background: var(--z-surface-hover); }
    button[aria-selected="true"] {
      background: var(--z-surface-hover);
      border-left-color: var(--z-accent);
    }
    .time { color: var(--z-text-subtle); }
    .kind {
      color: var(--z-text-muted);
      letter-spacing: 0.04em;
      font-size: 11px;
    }
    .step { color: var(--z-text-subtle); }
    .summary {
      overflow: hidden;
      text-overflow: ellipsis;
      color: var(--z-text);
    }
    .summary .detail {
      color: var(--z-text-muted);
    }
    .dur, .usage { color: var(--z-text-muted); text-align: right; }
    .status { text-align: right; }
    .status.completed { color: var(--z-success); }
    .status.failed { color: var(--z-danger); }
    .status.paused, .status.limit_reached { color: var(--z-warning); }
    .status.incomplete, .status.started { color: var(--z-accent); }
    .status.unresolved, .status.unknown { color: var(--z-text-muted); }
    /* Row-level emphasis for non-happy states: border + glyph, not just hue. */
    button.state-failed { background: rgba(212, 104, 95, 0.07); }
    button.state-unresolved { background: rgba(211, 160, 79, 0.06); }
    button.state-paused { background: rgba(211, 160, 79, 0.09); }
  `;ht([p({attribute:!1})],H.prototype,"row",2);ht([p({type:Boolean})],H.prototype,"selected",2);H=ht([x("zuaef-event-row")],H);var je=Object.defineProperty,Re=Object.getOwnPropertyDescriptor,F=(e,t,s,r)=>{for(var o=r>1?void 0:r?Re(t,s):t,n=e.length-1,i;n>=0;n--)(i=e[n])&&(o=(r?i(t,s,o):i(o))||o);return r&&o&&je(t,s,o),o};let S=class extends ${constructor(){super(...arguments),this.projection=null,this.loading=!1,this.selectedEventId="",this.error=""}select(e){this.dispatchEvent(new CustomEvent("event-selected",{detail:e.detail,bubbles:!0,composed:!0}))}render(){const e=this.projection?.run;return a`
      <header>
        <h2>${e?e.display_label:"Trajectory"}</h2>
        ${e?a`<zuaef-status-badge .status=${e.status}></zuaef-status-badge>`:""}
        ${e&&e.model?a`<span class="model">${e.model}</span>`:""}
      </header>
      ${this.projection?.diagnostics?.length?this.projection.diagnostics.map(t=>a`<div class="diag">${t}</div>`):""}
      <div class="scroll">
        ${this.error?a`<div class="state error">${this.error}</div>`:this.loading?a`<div class="state">Loading trajectory…</div>`:this.projection?this.projection.timeline.length===0?a`<div class="state">
                    No step events persisted for this run — only receipt-level facts exist.
                  </div>`:this.projection.timeline.map(t=>a`
                      <zuaef-event-row
                        role="option"
                        .row=${t}
                        ?selected=${t.id===this.selectedEventId}
                        @event-selected=${s=>this.select(s)}
                      ></zuaef-event-row>
                    `):a`<div class="state">Select a run to inspect its trajectory.</div>`}
      </div>
    `}};S.styles=y`
    :host {
      display: flex;
      flex-direction: column;
      min-height: 0;
    }
    header {
      display: flex;
      align-items: baseline;
      gap: var(--z-space-3);
      padding: var(--z-space-2) var(--z-space-3);
      border-bottom: 1px solid var(--z-border);
      min-width: 0;
    }
    h2 {
      margin: 0;
      font-size: 13px;
      font-weight: 600;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .diag {
      padding: var(--z-space-1) var(--z-space-3);
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-warning);
      border-bottom: 1px solid var(--z-border);
      overflow-wrap: anywhere;
    }
    .scroll {
      flex: 1;
      overflow-y: auto;
      min-height: 0;
      padding-top: var(--z-space-1);
    }
    .state {
      padding: var(--z-space-4) var(--z-space-3);
      color: var(--z-text-muted);
    }
    .error {
      color: var(--z-danger);
    }
  `;F([p({attribute:!1})],S.prototype,"projection",2);F([p({type:Boolean})],S.prototype,"loading",2);F([p()],S.prototype,"selectedEventId",2);F([p()],S.prototype,"error",2);S=F([x("zuaef-trajectory-view")],S);var Te=Object.defineProperty,Ue=Object.getOwnPropertyDescriptor,w=(e,t,s,r)=>{for(var o=r>1?void 0:r?Ue(t,s):t,n=e.length-1,i;n>=0;n--)(i=e[n])&&(o=(r?i(t,s,o):i(o))||o);return r&&o&&Te(t,s,o),o};let v=class extends ${constructor(){super(...arguments),this.ui=le,this.runs=[],this.nextCursor=null,this.loadingMore=!1,this.projection=null,this.projectionLoading=!1,this.projectionError=""}connectedCallback(){super.connectedCallback(),this.reloadRuns()}async reloadRuns(){try{const e=await st.listRuns();this.runs=e.runs,this.nextCursor=e.next_cursor,!this.ui.selectedRunId&&this.runs.length>0?this.selectRun(this.runs[0].run_id):this.ui.selectedRunId&&this.reloadProjection(this.ui.selectedRunId)}catch(e){this.projectionError=`Failed to load runs: ${rt(e)}`}}async loadMore(e){this.loadingMore=!0;try{const t=await st.listRuns(e),s=new Set(this.runs.map(r=>r.run_id));this.runs=[...this.runs,...t.runs.filter(r=>!s.has(r.run_id))],this.nextCursor=t.next_cursor}catch(t){this.projectionError=`Failed to load more runs: ${rt(t)}`}finally{this.loadingMore=!1}}async reloadProjection(e){this.projectionLoading=!this.projection||this.projection.run.run_id!==e,this.projectionLoading&&(this.projectionError="");try{this.projection=await st.getRun(e),this.projectionError="",document.title=`${this.projection.run.display_label} — ZUAEF Console`}catch(t){this.projectionError=`Failed to load run: ${rt(t)}`}finally{this.projectionLoading=!1}}patchUi(e){this.ui={...this.ui,...e}}selectRun(e){e!==this.ui.selectedRunId&&(this.patchUi({selectedRunId:e,selectedEventId:void 0}),this.reloadProjection(e))}render(){const e=this.projection?.run??null,t=e?[e.model??"model unknown",e.profile??"profile unknown"].join(" · "):"";return a`
      <header class="topbar">
        <span class="brand">ZUAEF</span>
        <span class="meta">${t}</span>
        <span class="spacer"></span>
        <button class="refresh" @click=${()=>{this.refresh()}}>
          Refresh
        </button>
      </header>
      <div class="panes">
        <zuaef-run-list
          .runs=${this.runs}
          .selectedRunId=${this.ui.selectedRunId??""}
          .nextCursor=${this.nextCursor}
          .loadingMore=${this.loadingMore}
          .filter=${this.ui.runFilter??""}
          @run-selected=${s=>this.selectRun(s.detail.runId)}
          @run-filter=${s=>this.patchUi({runFilter:s.detail.value})}
          @load-more=${()=>{this.nextCursor&&this.loadMore(this.nextCursor)}}
        ></zuaef-run-list>

        <zuaef-trajectory-view
          .projection=${this.projection}
          .loading=${this.projectionLoading}
          .selectedEventId=${this.ui.selectedEventId??""}
          .error=${this.projectionError}
          @event-selected=${s=>this.patchUi({selectedEventId:s.detail.rowId})}
        ></zuaef-trajectory-view>

        <zuaef-inspector
          .projection=${this.projection}
          .selectedEventId=${this.ui.selectedEventId??""}
          .inspectorTab=${this.ui.inspectorTab}
          @tab-selected=${s=>this.patchUi({inspectorTab:s.detail.tab})}
        ></zuaef-inspector>
      </div>
      <zuaef-artifact-bar
        .artifacts=${this.projection?.artifacts??[]}
        .pause=${this.projection?.pause??null}
      ></zuaef-artifact-bar>
    `}async refresh(){await this.reloadRuns()}};v.styles=y`
    :host {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr) auto;
      height: 100vh;
    }
    .topbar {
      display: flex;
      align-items: center;
      gap: var(--z-space-4);
      padding: var(--z-space-2) var(--z-space-3);
      border-bottom: 1px solid var(--z-border);
      background: var(--z-surface);
    }
    .brand {
      font-weight: 700;
      letter-spacing: 0.12em;
      font-size: 13px;
    }
    .topbar .spacer { flex: 1; }
    .meta {
      font-family: var(--z-font-mono);
      font-size: 11px;
      color: var(--z-text-muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .refresh {
      border: 1px solid var(--z-border);
      border-radius: var(--z-radius);
      padding: 2px var(--z-space-2);
      color: var(--z-text-muted);
      font-size: 12px;
    }
    .refresh:hover { color: var(--z-text); background: var(--z-surface-hover); }
    .panes {
      display: grid;
      grid-template-columns: 264px minmax(0, 1fr) 380px;
      min-height: 0;
    }
    @media (max-width: 1100px) {
      .panes { grid-template-columns: 220px minmax(0, 1fr) 320px; }
    }
  `;w([p({attribute:!1})],v.prototype,"ui",2);w([R()],v.prototype,"runs",2);w([R()],v.prototype,"nextCursor",2);w([R()],v.prototype,"loadingMore",2);w([R()],v.prototype,"projection",2);w([R()],v.prototype,"projectionLoading",2);w([R()],v.prototype,"projectionError",2);v=w([x("zuaef-console")],v);function rt(e){return e instanceof Error?e.message:String(e)}
