/**
 * Acquire Javascript Library. This provides some native JS classes
 * that match the API of the Acquire.Client Python library. This
 * is a client-only library, so only provides matching classes
 * for (some) of the classes available in Acquire.Client
 */

async function test_acquire()
{
    try
    {
        /*var wallet = new Wallet();

        //wallet.clear();

        var service = await wallet.get_service({service_uid:"a0-a0"});

        console.log(service);

        service = await wallet.get_service({service_url:service.canonical_url()});

        console.log(service);

        id_service = await wallet.get_service({service_uid:"a0-a1"});

        console.log(id_service);*/

        user = new User({username:"chryswoods"});

        console.log(user);

        result = await user.request_login();

        console.log(result);
    }
    catch(err)
    {
        console.log(`UNCAUGHT EXCEPTION: ${err}`);
        var obj = JSON.parse(JSON.stringify(err));
        console.log(obj);
    }
}
