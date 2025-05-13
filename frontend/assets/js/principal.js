//frontend/assets/js/principal.js

//Validación de autenticación al cargar
if (!localStorage.getItem('auth')) {
  window.location.href = 'login.html';
}

//Seleccionar línea
function getLeaderLineSvg(linea) {
  const allLines = document.querySelectorAll('svg.leader-line');
  return Array.from(allLines).find(svg => {
    return svg.__leaderLine === linea;
  });
}


//Funcionalidad boton Salir
document.addEventListener('DOMContentLoaded', () => {
  const logoutBtn = document.getElementById('logoutButton');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      localStorage.removeItem('auth');
      window.location.href = 'login.html';
    });
  }
});

document.addEventListener('DOMContentLoaded', () => {
  console.log('DOMContentLoaded disparado');
  
  // Referencias al DOM
  const numImagesParsed = document.getElementById('numImages');
  const numGroupsParsed = document.getElementById('numGroups');
  const numMembersParsed = document.getElementById('numMembers');
  const studentTutorVal = document.getElementById('studentTutor');
  const imagenesContainer = document.getElementById('imagenesContainer');
  const gruposContainer = document.getElementById('gruposContainer');
  const miembrosContainer = document.getElementById('miembrosContainer');
  
  // Estado
  let originElem = null;
  let originPoint = null;
  let selectedKey = null;
  window.connections = new Map(); // "fromId|toId" → { linea, fromId, toId }
  //Eliminar relación/línea
  document.addEventListener('keydown', e => {
    if ((e.key === 'Delete' || e.key === 'Backspace') && selectedKey) {
      const { linea } = connections.get(selectedKey);
      linea.remove();
      connections.delete(selectedKey);
      selectedKey = null;
    }
  });

  // Elimina todas las líneas existentes|
  function clearAllLines() {
    connections.forEach(({ linea }) => {
      try {
        linea.remove();
      } catch (e) {
        console.warn("No se pudo eliminar línea LeaderLine:", e);
      }
    });
    connections.clear();
  
    // Elimina todos los SVGs residuales insertados por LeaderLine
    const svgs = document.querySelectorAll('svg.leader-line');
    svgs.forEach(svg => {
      try {
        svg.remove();
      } catch (e) {
        console.warn("No se pudo eliminar SVG residual:", e);
      }
    });
  
    // Reiniciar estado
    selectedKey = null;
    originElem  = null;
    originPoint = null;
  }  
  
  // Reconstruye todos los contenedores dinámicos
  function actualizarTodosContenedores() {
    clearAllLines();
    imagenesContainer.innerHTML = '';
    gruposContainer.innerHTML   = '';
    miembrosContainer.innerHTML = '';
    
    const numImg = Math.max(0, parseInt(numImagesParsed.value, 10) || 0);
    const numGrp = Math.max(0, parseInt(numGroupsParsed.value, 10) || 0);
    const numMbr = Math.max(0, parseInt(numMembersParsed.value, 10) || 0);
    
    for (let i = 0; i < numImg; i++) imagenesContainer.appendChild(crearElemento('imagen', i));
    
    for (let i = 0; i < numGrp; i++) {
      const div = crearElemento('grupo', i);
      gruposContainer.appendChild(div);
    }
    
    for (let i = 0; i < numMbr; i++) miembrosContainer.appendChild(crearElemento('miembro', i));
  }
  
  // Crea un bloque dinámico
  function crearElemento(tipo, idx) {
    const div = document.createElement('div');
    div.className = `dynamic-item ${tipo}`;
    div.id = `${tipo}-${idx}`;
    div.dataset.type = tipo;
    
    let html = '';
    if (tipo === 'imagen') {
        html = `
            <div class="connection-point right"></div>
            <label>Imagen ${idx + 1}</label>
            <div class="file-wrapper">
                <button type="button" class="custom-file-upload">Cargar TIFF</button>
                <input type="file" accept=".tif,.tiff" hidden>
                <span class="file-info"></span>
            </div>
        `;
    } else if (tipo === 'grupo') {
        html = `
            <div class="connection-point left"></div>
            <label>Grupo ${idx + 1}</label>
            <input type="text" placeholder="Nombre del grupo">
            <div class="connection-point right"></div>
        `;
    } else { // miembro
        html = `
            <div class="connection-point left"></div>
            <label>Miembro ${idx + 1}</label>
            <div class="email-wrapper">
                <input type="text" placeholder="usuario">
                <span class="email-suffix">@udistrital.edu.co</span>
            </div>
            <select class="rol-selector">
                ${studentTutorVal.value === 'si' 
                    ? '<option value="Estudiante">Estudiante</option><option value="Tutor">Tutor</option>' 
                    : '<option value="Contribuyente">Contribuyente</option><option value="Líder">Líder</option>'
                }
            </select>

        `;  
    }

    div.innerHTML = html;
    
    // Si es miembro, activar evento al cambiar rol
    if (tipo === 'miembro') {
      const select = div.querySelector('select.rol-selector');

      // Crear y agregar checkbox si el rol es Tutor o Líder
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'miembro-check';
      checkbox.title = 'Esquema contenedor de rásters';
      checkbox.style.position = 'absolute';
      checkbox.style.top = '6px';
      checkbox.style.right = '6px';
      checkbox.style.transform = 'scale(0.9)';
      checkbox.style.cursor = 'pointer';
      checkbox.style.display = 'none'; // por defecto oculto

      checkbox.addEventListener('change', (e) => {
        if (e.target.checked) {
          document.querySelectorAll('.miembro-check').forEach(cb => {
            if (cb !== e.target) cb.checked = false;
          });
        }
      });

      div.style.position = 'relative';
      div.appendChild(checkbox);

      // Mostrar u ocultar checkbox al cambiar rol + resetear relaciones
      select.addEventListener('change', () => {
        const valor = select.value;

        if (valor === 'Tutor' || valor === 'Líder') {
          checkbox.style.display = 'block';
        } else {
          checkbox.checked = false;
          checkbox.style.display = 'none';
        }

        // Solo puede estar marcado un checkbox a la vez
        document.querySelectorAll('.miembro-check').forEach(cb => {
          if (cb !== checkbox) cb.checked = false;
        });
      });
    }

    // Eventos de conexión
    div.querySelectorAll('.connection-point').forEach(pt =>
        pt.addEventListener('click', manejarClicPunto)
    );

    // Cargue de TIFF en imágenes
    if (tipo === 'imagen') {
        const btn = div.querySelector('.custom-file-upload');
        const inputFile = div.querySelector('input[type=file]');
        const info = div.querySelector('.file-info');
        
        btn.addEventListener('click', () => inputFile.click());
        inputFile.addEventListener('change', () => {
          const file = inputFile.files[0];
          if (!file) return;
        
          const ext = file.name.split('.').pop().toLowerCase();
          const baseName = file.name.split('.')[0];
        
          if (!['tif', 'tiff'].includes(ext)) {
            alert('⚠️ Solo archivos .tif o .tiff');
            inputFile.value = '';
            info.textContent = '';
            return;
          }
        
          if (!/^[a-z0-9]+$/.test(baseName)) {
            alert('⚠️ El nombre del archivo solo puede tener números y minúsculas');
            inputFile.value = '';
            info.textContent = '';
            return;
          }
        
          info.textContent = file.name;
        });        

    }

    return div;
  }

  // Lógica al hacer clic en un punto de conexión
  function manejarClicPunto(e) {
    const pt   = e.target;
    const elem = pt.closest('.dynamic-item');
    const tipo = elem.dataset.type;

    // Si no hay origen, lo asigna
    if (!originPoint) {
      originElem  = elem;
      originPoint = pt;
      pt.style.backgroundColor = '#FF4444';
      return;
    }

    const origTipo = originElem.dataset.type;
    const fromId = originElem.id;
    const toId   = elem.id;
    const key    = `${fromId}|${toId}`;

    // Validaciones para conexiones desde imagen
    if (origTipo === 'imagen') {
      const grupoId = toId;

      // 🚫 Validar si el grupo ya tiene otra imagen asociada
      const yaTieneImagen = Array.from(connections.values()).some(rel => {
        return rel.toId === grupoId && rel.fromId.startsWith('imagen');
      });

      if (yaTieneImagen) {
        alert('⚠️ El grupo ya tiene un ráster asociado');
        originPoint.style.backgroundColor = '#004080';
        originPoint = originElem = null;
        return;
      }
    }

    // Solo imagen→grupo o miembro→grupo
    if (!((origTipo === 'imagen' || origTipo === 'miembro') && tipo === 'grupo')) {
      originPoint.style.backgroundColor = '#004080';
      originPoint = originElem = null;
      return;
    }

    // Un grupo no puede tener más de un Tutor
    if (origTipo === 'miembro') {
      const grupoId = elem.id;

      // Validar si el miembro actual tiene rol Tutor
      const idxOrigen = parseInt(fromId.split('-')[1]);
      const selectOrigen = document.querySelector(`#miembro-${idxOrigen} select`);
      const rolOrigen = selectOrigen?.value;

      // Si el miembro actual es Tutor, validar si ya hay otro Tutor en ese grupo
      /*if (rolOrigen === 'Tutor') {
        const yaTieneOtroTutor = Array.from(connections.values()).some(rel => {
          return rel.toId === grupoId && rel.fromId.startsWith('miembro') && (() => {
            const idx = parseInt(rel.fromId.split('-')[1]);
            const select = document.querySelector(`#miembro-${idx} select`);
            const rol = select?.value;
            return rol === 'Tutor' && rel.fromId !== fromId;
          })();
        });

        if (yaTieneOtroTutor) {
          alert('⚠️ El grupo ya tiene un miembro con rol de Tutor');
          originPoint.style.backgroundColor = '#004080';
          originPoint = originElem = null;
          return;
        }
      }*/
    }

    // Evitar duplicados
    if (connections.has(key)) {
      alert('⚠️ Estos elementos ya están conectados');
      originPoint.style.backgroundColor = '#004080';
      originPoint = originElem = null;
      return;
    }

    // Dibuja la línea
    const linea = new LeaderLine(
      LeaderLine.pointAnchor(originPoint, { x: '100%', y: '50%' }),
      LeaderLine.pointAnchor(pt, { x: '0%', y: '50%' }),
      { 
          color: '#004080', 
          size: 3, 
          path: 'fluid',
          startPlug: 'disc', 
          endPlug: 'arrow3', 
          zIndex: 1000 
      }
    );

    // Detectar el nodo SVG real
    const svgElem = getLeaderLineSvg(linea);
    if (svgElem) {
        svgElem.style.pointerEvents = 'all';
        svgElem.style.cursor = 'pointer';
        svgElem.addEventListener('click', ev => {
            ev.stopPropagation();
            if (selectedKey) {
                connections.get(selectedKey).linea.setOptions({ color: '#004080' });
            }
            selectedKey = key;
            linea.setOptions({ color: '#FF4444' });
        });
    }

    connections.set(key, { fromId, toId, linea });
    originPoint.style.backgroundColor = '#004080';
    originPoint = originElem = null;
  }

  // Deselecciona al hacer clic fuera
  document.addEventListener('click', e => {
    if (selectedKey && !e.target.closest('.dynamic-item')) {
      connections.get(selectedKey).linea.setOptions({ color: '#004080' });
      selectedKey = null;
    }
    if (originPoint && !e.target.closest('.connection-point')) {
      originPoint.style.backgroundColor = '#004080';
      originPoint = originElem = null;
    }
  });

  // Inicialización
  actualizarTodosContenedores();
  [numImagesParsed, numGroupsParsed, numMembersParsed].forEach(inp => {
    inp.addEventListener('input',  actualizarTodosContenedores);
    inp.addEventListener('change', actualizarTodosContenedores);
  });
  studentTutorVal.addEventListener('change', actualizarTodosContenedores);
});

//Funcionalidad del botón Confirmar
document.addEventListener('DOMContentLoaded', () => {
  const confirmBtn = document.getElementById('btn-confirm');
  if (!confirmBtn) return;

  confirmBtn.addEventListener('click', async () => {
    const errors = [];

    // Recolección de campos
    const projectName   = document.getElementById('projectName')?.value.trim();
    const studentTutor  = document.getElementById('studentTutor')?.value;
    const ciafLevel     = document.getElementById('ciafLevel')?.value;
    const numImages     = parseInt(document.getElementById('numImages')?.value || 0);
    const numGroups     = parseInt(document.getElementById('numGroups')?.value || 0);
    const numMembers    = parseInt(document.getElementById('numMembers')?.value || 0);

    // Validar campos principales
    if (!projectName) errors.push("Ingresar nombre del proyecto");
    else if (!/^[a-z0-9]+$/.test(projectName)) errors.push("El nombre del proyecto solo debe contener minúsculas y números");

    if (!studentTutor) errors.push("Seleccionar opción ¿Es estudiante-tutor?");
    else if (!["si", "no"].includes(studentTutor)) errors.push("Valor inválido en ¿Es estudiante-tutor?");

    if (!ciafLevel) errors.push("Seleccionar nivel CIAF");

    if (numImages <= 0) errors.push("Debe indicar al menos una imagen");
    if (numGroups <= 0) errors.push("Debe indicar al menos un grupo");
    if (numMembers <= 0) errors.push("Debe indicar al menos un miembro");

    // Validar nombres de grupos
    const gruposInputs = document.querySelectorAll("#gruposContainer input[type=text]");
    let hayGruposSinNombre = false;
    gruposInputs.forEach((input) => {
      const val = input.value.trim();
      if (!val) hayGruposSinNombre = true;
      else if (!/^[a-z0-9]+$/.test(val)) {
        errors.push("Nombre de grupo invalido, solo ingresar números y minúsculas");
      }
    });

    if (hayGruposSinNombre) {
      errors.push("Hay grupos sin nombrar");
    }

    // Validar nombres de miembros
    const miembrosInputs = document.querySelectorAll("#miembrosContainer input[type=text]");
    let hayMiembrosSinNombre = false;
    miembrosInputs.forEach((input) => {
      const val = input.value.trim();
      if (!val) hayMiembrosSinNombre = true;
      else if (!/^[a-z0-9]+$/.test(val)) {
        errors.push("Nombre de Miembro invalido, solo ingresar números y minúsculas");
      }
    });

    if (hayMiembrosSinNombre) {
      errors.push("Hay miembros sin nombrar");
    }

    // Validar que no falten imágenes por cargar
    const imagenWrappers = document.querySelectorAll("#imagenesContainer input[type=file]");
    let faltanImagenes = false;

    imagenWrappers.forEach((input) => {
      const file = input.files[0];
      if (!file) {
        faltanImagenes = true;
      } 
    });

    if (faltanImagenes) {
      errors.push("Faltan imágenes por cargar");
    }


    // Validar que no haya imágenes con el mismo nombre (ignorando la extensión)
    const nombresBase = [];
    const nombresDuplicados = new Set();

    imagenWrappers.forEach((input) => {
      const file = input.files[0];
      if (file) {
        const nombreBase = file.name.split('.').slice(0, -1).join('.'); // elimina la extensión
        if (nombresBase.includes(nombreBase)) {
          nombresDuplicados.add(nombreBase);
        }
        nombresBase.push(nombreBase);
      }
    });

    if (nombresDuplicados.size > 0) {
      const duplicados = Array.from(nombresDuplicados).join(", ");
      errors.push(`Se han cargado varias imágenes con el mismo nombre: ${duplicados}`);
    }

    // Mostrar errores si los hay
    if (errors.length > 0) {
      alert("⚠️ Errores detectados:\n" + errors.join("\n"));
      return;
    }

    // Recolección de relaciones
    const rasterRelations = [];
    const memberRelations = [];

    if (!(window.connections instanceof Map) || window.connections.size === 0) {
      alert("No se han definido relaciones aún.");
      return;
    }

    for (const [key, { fromId, toId }] of window.connections.entries()) {

      if (fromId.startsWith("imagen") && toId.startsWith("grupo")) {
        rasterRelations.push({ source: fromId, target: toId });
      }

      if (fromId.startsWith("miembro") && toId.startsWith("grupo")) {
        memberRelations.push({ source: fromId, target: toId });
      }
    }

    // Validar que cada imagen esté relacionada al menos a un grupo
    const imagenNoRelacionada = [];
    for (let i = 0; i < numImages; i++) {
      const id = `imagen-${i}`;
      const tieneRelacion = rasterRelations.some(rel => rel.source === id);
      if (!tieneRelacion) {
        const nombreArchivo = document.querySelector(`#${id} .file-info`)?.textContent || `(Imagen ${i + 1})`;
        imagenNoRelacionada.push(nombreArchivo);
      }
    }

    // Validar que cada grupo tenga al menos una imagen relacionada
    const gruposSinImagen = [];
    for (let i = 0; i < numGroups; i++) {
      const idGrupo = `grupo-${i}`;
      const tieneRelacion = rasterRelations.some(rel => rel.target === idGrupo);
      if (!tieneRelacion) {
        const nombreGrupo = document.querySelector(`#${idGrupo} input`)?.value?.trim() || idGrupo;
        gruposSinImagen.push(nombreGrupo);
      }
    }

    if (gruposSinImagen.length > 0) {
      alert("⚠️ Los siguientes grupos no tienen imágenes relacionadas:\n\n" + gruposSinImagen.join("\n"));
      return;
    }

    if (imagenNoRelacionada.length > 0) {
      alert("⚠️ Las siguientes imágenes no están relacionadas con ningún grupo:\n\n" + imagenNoRelacionada.join("\n"));
      return;
    }

    // Validar que cada grupo tenga al menos un miembro relacionado
    const gruposSinMiembro = [];
    for (let i = 0; i < numGroups; i++) {
      const idGrupo = `grupo-${i}`;
      const tieneRelacion = memberRelations.some(rel => rel.target === idGrupo);
      if (!tieneRelacion) {
        const nombreGrupo = document.querySelector(`#${idGrupo} input`)?.value || `(Grupo ${i + 1})`;
        gruposSinMiembro.push(nombreGrupo);
      }
    }

    if (gruposSinMiembro.length > 0) {
      alert("⚠️ Los siguientes grupos no tienen miembros relacionados:\n\n" + gruposSinMiembro.join("\n"));
      return;
    }

    // Validar que cada miembro esté relacionado a al menos un grupo (excepto Tutor o Líder)
    const miembrosSinGrupo = [];
    for (let i = 0; i < numMembers; i++) {
      const idMiembro = `miembro-${i}`;
      const select = document.querySelector(`#${idMiembro} select`);
      const rol = select?.value || '';
      
      if (rol === 'Tutor' || rol === 'Líder') continue;

      const tieneRelacion = memberRelations.some(rel => rel.source === idMiembro);
      if (!tieneRelacion) {
        const nombre = document.querySelector(`#${idMiembro} input`)?.value || `(Miembro ${i + 1})`;
        miembrosSinGrupo.push(nombre);
      }
    }

    if (miembrosSinGrupo.length > 0) {
      alert("⚠️ Los siguientes miembros no están relacionados con ningún grupo:\n\n" + miembrosSinGrupo.join("\n"));
      return;
    }

    try {
      // Definir miembrosList y rasterGroupMappings primero
      const miembrosList = [];
      const miembrosInputs = document.querySelectorAll("#miembrosContainer input[type=text]");
      miembrosInputs.forEach((input, i) => {
          const username = input.value.trim();
          const role = document.querySelector(`#miembro-${i} select`)?.value || '';
          const groupRel = memberRelations.find(r => r.source === `miembro-${i}`);
          
          miembrosList.push({
              id: `miembro-${i}`,
              email: `${username}@udistrital.edu.co`,
              role,
              groupId: groupRel?.target || null
          });
      });

      const gruposInputs = document.querySelectorAll("#gruposContainer input[type=text]");
      const gruposMap = new Map();
      gruposInputs.forEach((input, i) => {
        gruposMap.set(`grupo-${i}`, input.value.trim());
      });

      const imagenWrappers = document.querySelectorAll("#imagenesContainer input[type=file]");
      const imagenMap = new Map();
      imagenWrappers.forEach((input, i) => {
        const file = input.files[0];
        imagenMap.set(`imagen-${i}`, file?.name || '');
      });

      const rasterGroupMappings = rasterRelations.reduce((acc, rel) => {
        const imageName = imagenMap.get(rel.source);
        const groupName = gruposMap.get(rel.target);
        const baseName = imageName?.split('.')[0] || '';
    
        let entry = acc.find(e => e.imageId === rel.source);
        if (!entry) {
            entry = {
                servantMap: `${projectName}-${Date.now()}-${rel.source}`,
                imageId: rel.source,
                imageName,
                groups: []
            };
            acc.push(entry);
        }
    
        entry.groups.push({
            groupId: rel.target,
            groupName,
            segmentacionName: `${groupName}${baseName}`
        });
    
        return acc;
    }, []);

      const memberGroupMappings = memberRelations.map(rel => ({
        memberId: rel.source,
        groupId: rel.target
      }));

      // Detectar miembro con checkbox marcado (Tutor o Líder)
      const checkSeleccionado = Array.from(document.querySelectorAll('.miembro-check')).find(cb => cb.checked);
      if (!checkSeleccionado) {
        alert("⚠️ Debe seleccionar un miembro Tutor/Líder como esquema contenedor de imágenes.");
        return;
      }

      const miembroContenedor = checkSeleccionado.closest('.dynamic-item');
      const input = miembroContenedor.querySelector('input[type="text"]');
      const grupoContenedorNombre = input?.value?.trim();

      if (!grupoContenedorNombre || !/^[a-z0-9]+$/.test(grupoContenedorNombre)) {
        alert("⚠️ El nombre del miembro seleccionado no es válido para esquema contenedor");
        return;
      }

      // Payload completo para creación
      const fecha = obtenerFechaActualYYYYMMDD();
      const nombreFinalProyecto = `${projectName}${fecha}`;
      const finalPayload = {
        projectName: nombreFinalProyecto,
        studentTutor,
        ciafLevel: parseInt(ciafLevel),
        numImages,
        numGroups,
        numMembers,
        groupNames: Array.from(gruposInputs).map(input => input.value.trim()),
        rasterGroupMappings,
        memberGroupMappings,
        members: miembrosList,
        grupoContenedor: grupoContenedorNombre
      };   

      // Construir FormData con archivos TIFF cargados
      const formData = new FormData();
      formData.append("projectName", nombreFinalProyecto);
      imagenWrappers.forEach((input, i) => {
        const file = input.files[0];
        if (file) {
          formData.append("files", file);
        }
      });

      // Validar que haya archivos en el formData
      if ([...formData.entries()].length === 0) {
        alert("⚠️ No se encontraron archivos TIFF para subir.");
        return;
      }

      try {
        const uploadResponse = await fetch('/api/projects/upload-tiffs', {
          method: 'POST',
          body: formData
        });
        const uploadResult = await uploadResponse.json();
        
        if (!uploadResponse.ok || !uploadResult.success) {
          alert("❌ Error al cargar archivos TIFF: " + (uploadResult.detail || 'Desconocido'));
          return;
        }
      } 

      catch (err) {
        console.error(err);
        alert("Error de conexión al cargar TIFFs");
        return;
      }

  // Creación final del proyecto
  try {
    console.log("Final Payload JSON:", JSON.stringify(finalPayload, null, 2));
    const createResponse = await fetch('/api/projects/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(finalPayload)
    });
 
    let createResult;
    try {
      // Intenta decodificar JSON, si es posible
      createResult = await createResponse.json();
    }
    
    catch {
      const rawText = await createResponse.text();
      alert("❌ Error inesperado del servidor:\n" + rawText);
      return;     
    }

if (!createResponse.ok || !createResult.success) {
  const erroresImagenes = Array.isArray(createResult.errores) && createResult.errores.length > 0;

  if (erroresImagenes) {
    let mensaje = "❌ El proyecto no se creó por errores en las imágenes:\n\n";
    for (const err of createResult.errores) {
      const descripcion = err.error || "Error desconocido";
      mensaje += `• ${err.imagen}: ${descripcion}\n`;
    }
    alert(mensaje);
  } else {
    let mensaje = "❌ Error en la creación del proyecto.";

    if (createResult.detail || createResult.msg) {
      mensaje += "\n\n" + (createResult.detail || createResult.msg);
    } else {
      mensaje += "\n\nNo se recibió un mensaje claro del servidor. Revisa la consola o contacta al administrador.";
    }

    console.error("Error completo recibido del backend:", createResult);
    alert(mensaje);
  }

  return;
}

    // ✅ Éxito
    let resumen = "✅ Proyecto creado exitosamente.\n";
    if (Array.isArray(createResult.resumen_rasters)) {
      resumen += "\n🗂 Resultado por imagen:\n";
      for (const r of createResult.resumen_rasters) {
        if (r.status === "éxito") {
          resumen += `• ${r.imagen}: ✅ (${r.duracion_segundos} seg)\n`;
        } else {
          resumen += `• ${r.imagen}: ❌ ${r.error}\n`;
        }
      }
    }

    alert(resumen);

  } 
      
  catch (err) {
    alert("❌ Error de red al crear el proyecto. Verifica tu conexión.");
  }
      
  } catch (err) {
    console.error(err);
    alert("Error de conexión con el servidor.");
  }
  });
});


//Restablecer relaciones y checkboxes
function resetearRelacionesYCheckboxes() {
  // Eliminar todas las líneas visuales
  connections.forEach(({ linea }) => {
    linea.remove();
  });

  // Vaciar conexiones
  connections.clear();
  selectedKey = null;

  // Quitar el estado de "checked" y ocultar el checkbox, pero **no eliminarlo**
  document.querySelectorAll('.miembro-check').forEach(cb => {
    cb.checked = false;
    cb.style.display = 'none';
  });
}

//Obtener fecha actual
function obtenerFechaActualYYYYMMDD() {
  const hoy = new Date();
  const yyyy = hoy.getFullYear();
  const mm = String(hoy.getMonth() + 1).padStart(2, '0');
  const dd = String(hoy.getDate()).padStart(2, '0');
  return `${yyyy}${mm}${dd}`;
}
