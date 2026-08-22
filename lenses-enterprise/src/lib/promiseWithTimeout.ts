/**
 * Race `promise` against a timer. Used for wizard session bootstrap so invalid probe ids
 * cannot leave the UI spinning indefinitely if the network hangs.
 */
export function promiseWithTimeout<T>(promise: Promise<T>, ms: number, timeoutError: () => Error): Promise<T> {
  return new Promise((resolve, reject) => {
    const t = window.setTimeout(() => {
      reject(timeoutError())
    }, ms)
    promise.then(
      (v) => {
        window.clearTimeout(t)
        resolve(v)
      },
      (e) => {
        window.clearTimeout(t)
        reject(e)
      },
    )
  })
}
