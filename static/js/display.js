window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  data() {
    return {
      paymentReq: null,
      redirectUrl: null,
      flatrate: form_flatrate,
      formDialog: {
        show: false,
        data: {
          name: '',
          email: '',
          text: ''
        },
        dismissMsg: null,
        paymentChecker: null
      },
      receive: {
        show: false,
        status: 'pending',
        paymentReq: null
      },
      wallet: {
        inkey: ''
      },
      cancelListener: () => {}
    }
  },
  computed: {
    amountWords() {
      if (this.formDialog.data.text.length == '') {
        return '0 Sats to pay'
      } else {
        let sats = 0
        const regex = /\s+/gi
        const nwords = this.formDialog.data.text
          .trim()
          .replace(regex, ' ')
          .split(' ').length
        if (this.flatrate) {
          sats = form_amount
        } else {
          sats = nwords * form_amount
        }
        this.formDialog.data.sats = sats
        return sats + ' Sats to pay'
      }
    }
  },
  methods: {
    resetForm(e) {
      e.preventDefault()
      this.formDialog.data.name = ''
      this.formDialog.data.email = ''
      this.formDialog.data.text = ''
    },
    closeReceiveDialog() {
      this.receive.show = false
      this.formDialog.dismissMsg()
      clearInterval(this.formDialog.paymentChecker)
    },
    submitInvoice() {
      const dialog = this.formDialog
      axios
        .post(`/lnticket/api/v1/tickets/${form_id}`, {
          form: form_id,
          name: this.formDialog.data.name,
          email: this.formDialog.data.email,
          ltext: this.formDialog.data.text,
          sats: this.formDialog.data.sats
        })
        .then(response => {
          this.paymentReq = response.data.payment_request
          this.paymentCheck = response.data.payment_hash

          dialog.dismissMsg = Quasar.Notify.create({
            timeout: 0,
            message: 'Waiting for payment...'
          })
          this.receive = {
            show: true,
            status: 'pending',
            paymentReq: this.paymentReq
          }
          dialog.paymentChecker = setInterval(() => {
            axios
              .get('/lnticket/api/v1/tickets/' + response.data.payment_hash)
              .then(res => {
                if (res.data.paid) {
                  clearInterval(dialog.paymentChecker)
                  dialog.dismissMsg()
                  this.receive.show = false
                  this.formDialog.data.name = ''
                  this.formDialog.data.email = ''
                  this.formDialog.data.text = ''
                  Quasar.Notify.create({
                    type: 'positive',
                    message: 'Sats received, thanks!',
                    icon: 'thumb_up'
                  })
                }
              })
          }, 3000)
        })
        .catch(function (error) {
          LNbits.utils.notifyApiError(error)
        })
    }
  },
  created() {
    this.wallet.inkey = form_wallet
  }
})
