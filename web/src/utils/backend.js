import { spawn } from '@tauri-apps/api/shell'
import { platform } from '@tauri-apps/api/os'

let backendProcess = null

export async function startBackend() {
  if (backendProcess) {
    return
  }

  try {
    const osType = await platform()
    let pythonPath = 'python3'
    
    if (osType === 'windows') {
      pythonPath = 'python'
    }

    backendProcess = await spawn(pythonPath, [
      '-m', 'p2plab.cli', 'serve', '--port', '8765'
    ], {
      cwd: process.cwd(),
      env: {
        PYTHONPATH: process.cwd()
      }
    })

    backendProcess.stdout.on('data', (data) => {
      console.log('Backend stdout:', data)
    })

    backendProcess.stderr.on('data', (data) => {
      console.log('Backend stderr:', data)
    })

    backendProcess.on('close', (code) => {
      console.log('Backend closed with code:', code)
      backendProcess = null
    })

    await new Promise(resolve => setTimeout(resolve, 3000))
    return true
  } catch (error) {
    console.error('Failed to start backend:', error)
    return false
  }
}

export async function stopBackend() {
  if (backendProcess) {
    try {
      await backendProcess.kill()
      backendProcess = null
    } catch (error) {
      console.error('Failed to stop backend:', error)
    }
  }
}
